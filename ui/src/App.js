import './App.css';
import React from 'react';

/*
TODO:
- stop stream before switching source.
- ui obviously.
- add a no image source option (default)
- streaming toggle is not working properly
*/

const Selector = ({options, selected, on_select}) => {
    const option_items = options.map(
        (val, idx) => {
            if (idx == selected) {
                return (
                    <option key={idx} value={idx} selected>{val}</option>
                );                
            }
            else {
                return (
                    <option key={idx} value={idx}>{val}</option>
                );
            }
        }
    );

    const on_change = (e) => {
        const i = e.target.value;
        on_select(options[i], i);
    };
                            
    return <select onChange={on_change}>{option_items}</select>;
};

const ImageSourceView = ({image_sources, source_idx, stream_width, stream_height, ctrl_state, update_ctrl_state}) => {
    const [isStreaming, setStreaming] = React.useState(false);
    const [sourceIdx, setSourceIdx] = React.useState(source_idx);
    const [streamWidth, setStreamWidth] = React.useState(stream_width);
    const [streamHeight, setStreamHeight] = React.useState(stream_height);
    const [undistort, setUndistort] = React.useState(false);

    const source_id = image_sources[sourceIdx];    
    const stream_url = `http://localhost:5000/video_stream/${source_id}?width=${streamWidth}&height=${streamHeight}&fps=5&undistort=${undistort}&ts=${Date.now()}`;
    
    const stopStreaming = () => {
        return fetch(`http://localhost:5000/stop_stream/${source_id}`)
            .then(update_ctrl_state);
    };
    
    const toggleStream = (e) => {
        if (isStreaming) {
            stopStreaming();
        }
        setStreaming(!isStreaming);
    };
    
    const toggleRecording = (e) => {
        if (ctrl_state["image_sources"][source_id].writing) {
            fetch(`http://localhost:5000/video_record/stop?src=${source_id}`)
                .then(update_ctrl_state);            
        }
        else {
            fetch(`http://localhost:5000/video_record/start?src=${source_id}`)
                .then(update_ctrl_state);            
        }
    };

    const onUndistortClick = (e) => {
        setUndistort(e.target.checked);
    };
    
    const switchSource = (name, idx) => {
        if (isStreaming) {
            stopStreaming()
                .then(() => setSourceIdx(idx));
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
    const record_btn_title = ctrl_state["image_sources"][source_id].writing ? "Stop Recording" : "Start Recording";
    
    return (
	<div>
          <label>Image Source: </label>
          <Selector options={image_sources} on_select={switchSource} selected={sourceIdx}/>
          <div className="stream" style={stream_div_style}>
            {stream}
          </div>	  
          <br/>
          <button onClick={toggleStream}>{stream_btn_title}</button>
          <button onClick={toggleRecording}>{record_btn_title}</button>
          <input type="checkbox"
                 name="undistort_checkbox"
                 checked={undistort}
                 onClick={onUndistortClick}
                 disabled={isStreaming}/>
          <label htmlFor="undistort_checkbox">Undistort</label>
        </div>
    );
};

const RecordAllControl = ({ctrl_state, update_ctrl_state}) => {
    // should only allow start if no one is recording
    // should allow stop if at least one is recording.
    let any_recording = false;
        
    for (const src_state of Object.values(ctrl_state["image_sources"])) {
        if (src_state["writing"]) {
            any_recording = true;
            break;
        }
    }

    const rec_btn_title = any_recording ? "Stop Recording" : "Start Recording";
    
    const toggleRecording = (e) => {

        if (any_recording) {
            fetch("http://localhost:5000/video_record/stop")
                .then(update_ctrl_state);
        }
        else {
            fetch("http://localhost:5000/video_record/start")
                .then(update_ctrl_state);
        }
    };
    
    return (
        <div>
          <button onClick={toggleRecording}>{rec_btn_title}</button>
        </div>
    );
};

const fetch_control_state = (on_fetch) => {
    return fetch("http://localhost:5000/state")
        .then(res => res.json());
};
                  
const App = () => {
    const [apiMsg, setApiMsg] = React.useState("Connecting to API...");
    const [error, setError] = React.useState("");
    const [ctrlState, setCtrlState] = React.useState(null);

    const update_ctrl_state = () => {
        return fetch_control_state().then(setCtrlState,
                                          err => setError([err.toString()]));
    };
    
    React.useEffect(() => {
        fetch("http://localhost:5000/")
            .then(res => res.text())
            .then(
                (res) => {
		    setApiMsg(res);
		},
                (error) => {
		    setError(error.toString());
		}
	    );

        update_ctrl_state();
    }, []);

    if (ctrlState === null)
        return null;

    const image_sources = Object.keys(ctrlState.image_sources);

    const imgSrcViews = image_sources.map((srcId, srcIdx) => {
        if (!ctrlState.image_sources[srcId].acquiring)
            return null;
        
        return <ImageSourceView image_sources={image_sources}
                                source_idx={srcIdx}
                                stream_width={640}
                                stream_height={480}
                                ctrl_state={ctrlState}
                                update_ctrl_state={update_ctrl_state}
                                key={srcId}/>;
    });
    
    return (
        <div className="App">
          {apiMsg}<br/>
          {error}
	  <RecordAllControl ctrl_state={ctrlState} update_ctrl_state={update_ctrl_state}/><br/>
          {imgSrcViews}
        </div>
    );
};

export default App;
