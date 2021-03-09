import React from 'react';
import {Selector} from './components.js';

export const StreamView = ({image_sources, source_idx, stream_width, stream_height}) => {
    const [isStreaming, setStreaming] = React.useState(false);
    const [sourceIdx, setSourceIdx] = React.useState(source_idx);
    const [streamWidth, setStreamWidth] = React.useState(stream_width);
    const [streamHeight, setStreamHeight] = React.useState(stream_height);
    const [undistort, setUndistort] = React.useState(false);

    const source_id = image_sources[sourceIdx];    
    const stream_url = `http://localhost:5000/video_stream/${source_id}?width=${streamWidth}&height=${streamHeight}&fps=5&undistort=${undistort}&ts=${Date.now()}`;
    
    const stopStreaming = () => {
        return fetch(`http://localhost:5000/stop_stream/${source_id}`)
    };
    
    const toggleStream = (e) => {
        if (isStreaming) {
            stopStreaming();
        }
        setStreaming(!isStreaming);
    };
    
    const onUndistortClick = (e) => {
        setUndistort(e.target.checked);
    };
    
    const switchSource = (name, idx) => {
        if (isStreaming) {
            stopStreaming()
                .then(() => setSourceIdx(idx));
        }
	else {
	    setSourceIdx(idx);
	}
    };
    
    React.useEffect(() => {
        return stopStreaming; // run on unmount
    }, []);
    
    const stream_div_style = {width: stream_width + "px", height: stream_height + "px"};
    
    const stream = isStreaming ?
	  (
              <img
	        src={stream_url}
                width={streamWidth}
                height={streamHeight}          
              />
          ) : null;
    
    const stream_btn_title = isStreaming ? "Stop Streaming" : "Start Streaming";
    console.log("Rendering stream view");
    return (
	<div className="component">
          <label>Image Source: </label>
          <Selector options={image_sources} on_select={switchSource} selected={sourceIdx}/>
          <div className="stream" style={stream_div_style}>
            {stream}
          </div>	  
          <br/>
          <button onClick={toggleStream}>{stream_btn_title}</button>
          <input type="checkbox"
                 name="undistort_checkbox"
                 checked={undistort}
                 onClick={onUndistortClick}
                 disabled={isStreaming}/>
          <label htmlFor="undistort_checkbox">Undistort</label>
        </div>
    );
}
