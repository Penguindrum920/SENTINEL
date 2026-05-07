export interface StitchComponentMount {
  unmount: () => void;
}

/**
 * Frontend-only wrapper for Google Stitch MCP UI components.
 * This is intentionally kept out of the market-data path.
 */
export class StitchMCPUI {
  mount(
    componentName: string,
    root: HTMLElement,
    props: Record<string, unknown> = {}
  ): StitchComponentMount {
    void componentName;
    void root;
    void props;

    return {
      unmount: () => undefined,
    };
  }
}
