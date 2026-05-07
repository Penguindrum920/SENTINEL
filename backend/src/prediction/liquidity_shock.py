"""Liquidity shock predictor using RandomForest classifier."""

from typing import Dict, List, Optional, Tuple
import pickle
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from .features import FeatureExtractor
from ..utils.logger import get_logger

logger = get_logger("liquidity_shock")

FEATURE_NAMES = [
    "spread_ratio",
    "depth_ratio",
    "volatility_ratio",
    "mm_inventory_stress",
    "active_mm_count",
    "time_to_close",
]

WARNING_LEVELS = {
    "safe": 80,
    "caution": 60,
    "warning": 40,
}


def _health_to_warning(health_score: float) -> str:
    if health_score >= 80:
        return "safe"
    elif health_score >= 60:
        return "caution"
    elif health_score >= 40:
        return "warning"
    else:
        return "critical"


class LiquidityShockPredictor:
    """
    Predicts liquidity shocks 60-90 seconds in advance using
    a RandomForest classifier trained on simulation data.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.feature_extractor = FeatureExtractor()
        self.model: Optional[RandomForestClassifier] = None
        self._model_path = model_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "models", "liquidity_model.pkl"
        )

        # Try to load existing model
        if os.path.exists(self._model_path):
            try:
                with open(self._model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Loaded pre-trained liquidity model")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    def predict(self, market_state: Dict) -> Dict:
        """
        Predict liquidity shock probability.

        Returns:
            Dict with probability, health_score, warning_level, features, timestamp
        """
        features = self.feature_extractor.extract_liquidity_features(market_state)
        timestamp = market_state.get("current_time", 0.0)

        if self.model is not None:
            X = np.array([[features[f] for f in FEATURE_NAMES]])
            proba = self.model.predict_proba(X)[0]
            # proba[1] = probability of shock
            shock_prob = float(proba[1]) if len(proba) > 1 else 0.0
        else:
            # Heuristic fallback when no trained model
            shock_prob = self._heuristic_probability(features)

        health_score = max(0.0, min(100.0, (1.0 - shock_prob) * 100))
        warning_level = _health_to_warning(health_score)

        return {
            "probability": round(shock_prob, 4),
            "health_score": round(health_score, 1),
            "warning_level": warning_level,
            "features": features,
            "timestamp": timestamp,
        }

    def _heuristic_probability(self, features: Dict[str, float]) -> float:
        """
        Rule-based fallback when no ML model is trained.
        Higher spread_ratio, lower depth_ratio, and higher vol = higher shock prob.
        """
        score = 0.0

        # High spread is bad
        if features["spread_ratio"] > 2.0:
            score += 0.3
        elif features["spread_ratio"] > 1.5:
            score += 0.15

        # Low depth is bad
        if features["depth_ratio"] < 0.5:
            score += 0.3
        elif features["depth_ratio"] < 0.8:
            score += 0.1

        # High volatility is bad
        if features["volatility_ratio"] > 2.0:
            score += 0.2
        elif features["volatility_ratio"] > 1.5:
            score += 0.1

        # MM stress is bad
        score += features["mm_inventory_stress"] * 0.2

        # Few active MMs is bad
        if features["active_mm_count"] <= 1:
            score += 0.15

        return min(1.0, score)

    def train(self, training_data: List[Dict]) -> None:
        """Train the RandomForest model on simulation data."""
        if not training_data:
            logger.warning("No training data provided")
            return

        X = np.array([[d["features"][f] for f in FEATURE_NAMES] for d in training_data])
        y = np.array([d["label"] for d in training_data])

        logger.info(f"Training on {len(X)} samples (shock rate: {y.mean():.2%})")

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=42,
        )
        self.model.fit(X, y)

        # Save model
        os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
        with open(self._model_path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {self._model_path}")

    def generate_training_data(self, num_simulations: int = 100) -> List[Dict]:
        """Generate labelled training data from simulations."""
        from ..agents.market_maker import MarketMakerAgent
        from ..agents.hft_agent import HFTAgent
        from ..agents.retail import RetailAgent
        from ..agents.noise import NoiseAgent
        from ..market.simulator import MarketSimulator

        all_samples: List[Dict] = []

        for sim_idx in range(num_simulations):
            agents = (
                [MarketMakerAgent(f"MM_{i}") for i in range(3)]
                + [HFTAgent(f"HFT_{i}") for i in range(5)]
                + [RetailAgent(f"R_{i}") for i in range(10)]
                + [NoiseAgent(f"N_{i}") for i in range(10)]
            )

            sim = MarketSimulator(agents, initial_price=100.0)
            sim.run(steps=3600)

            states = sim._state_history
            for i in range(len(states) - 60):
                features = self.feature_extractor.extract_liquidity_features(states[i])

                # Label: shock occurs in next 60 steps
                label = 0
                for j in range(i + 1, min(i + 61, len(states))):
                    future_features = self.feature_extractor.extract_liquidity_features(states[j])
                    if future_features["depth_ratio"] < 0.5 or future_features["spread_ratio"] > 3.0:
                        label = 1
                        break

                all_samples.append({"features": features, "label": label})

            if (sim_idx + 1) % 10 == 0:
                logger.info(f"Generated {sim_idx + 1}/{num_simulations} simulations")

        logger.info(f"Total training samples: {len(all_samples)}")
        return all_samples
