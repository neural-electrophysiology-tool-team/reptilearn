import { JSONEditor } from "svelte-jsoneditor/dist/jsoneditor.js";
import { useEffect, useRef } from "react";
import { classNames } from "./common";

// Adapted from https://codesandbox.io/s/svelte-jsoneditor-react-59wxz
export const RLJSONEditor = ({ className, ...props }) => {
  const refContainer = useRef(null);
  const refEditor = useRef(null);

  useEffect(() => {
    // create editor
    refEditor.current = new JSONEditor({
      target: refContainer.current,
      props
    });

    return () => {
      // destroy editor
      if (refEditor.current) {
        refEditor.current.destroy();
        refEditor.current = null;
      }
    };
  }, []);

  // update props
  useEffect(() => {
    if (refEditor.current) {
      refEditor.current.updateProps(props);
    }
  }, [props]);

  return <div className={classNames(className)} style={{
      '--jse-font-family-mono': 'Inconsolata', 
      '--jse-font-size-mono': '15px',
      '--jse-font-size': '14px',
      '--jse-context-menu-background': 'rgb(209, 213, 219)',
      '--jse-context-menu-color': 'black',
      '--jse-context-menu-button-background-highlight': 'rgb(107 114 128)',
      '--jse-context-menu-separator-color': 'rgb(107 114 128)',
      '--jse-context-menu-button-size': 'calc(1em + 2px)',
      '--jse-padding': '10px',
      '--jse-main-border': '0px',
    }} ref={refContainer}></div>;
}
