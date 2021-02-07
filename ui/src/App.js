import './App.css';
import React from 'react';

/*
TODO:
- stop stream before switching source.
- ui obviously.
- add a no image source option (default)
- streaming toggle is not working properly
*/

const ImageSourceSelector = ({onSelect}) => {
    const [imageSources, setImageSources] = React.useState([]);

    React.useEffect(() => {
        fetch("http://localhost:5000/list_image_sources")
            .then(res => res.json())
            .then(
                (res) => {
                    setImageSources(res);
                },
                (error) => {
                    setImageSources([error.toString()]);
                }
            );
    }, []);
    
    const option_items = imageSources.map((src, idx) => { return (<option key={src} value={idx}>{src}</option>); });

                                                                          return (
                                                                              <select onChange={onSelect}>
                                                                                {option_items}
                                                                              </select>
                                                                          );
};

const ImageSourceView = ({srcId, srcIdx, stream_width, stream_height, ctrl_state, update_ctrl_state}) => {
    const [isStreaming, setStreaming] = React.useState(false);

    const stream_url = `http://localhost:5000/video_stream/${srcIdx}/${stream_width}/${stream_height}?${Date.now()}`;
    
    const toggleStream = (e) => {
        if (isStreaming) {
            fetch(`http://localhost:5000/stop_stream/${srcIdx}`)
                .then(update_ctrl_state);
        }
        fetch(stream_url).then(update_ctrl_state);
        setStreaming(!isStreaming);
    };
    
    const toggleRecording = (e) => {
        if (ctrl_state["img_srcs"][srcId].writing) {
            fetch(`http://localhost:5000/video_writer/${srcIdx}/stop`)
                .then(update_ctrl_state);            
        }
        else {
            fetch(`http://localhost:5000/video_writer/${srcIdx}/start`)
                .then(update_ctrl_state);            
        }
    };
    
    const stream_div_style = {width: stream_width + "px", height: stream_height + "px"};
    
    const stream = isStreaming ?
	  (
              <img
	        src={stream_url}
                width={stream_width}
                height={stream_height}          
              />
          ) : null;
    
    const stream_btn_title = isStreaming ? "Stop Streaming" : "Start Streaming";
    const record_btn_title = ctrl_state["img_srcs"][srcId].writing ? "Stop Recording" : "Start Recording";
          
    return (
	<div>
	  <label>Image source: {srcId}</label>
          <div className="stream" style={stream_div_style}>
            {stream}
          </div>	  
          <br/>
          <button onClick={toggleStream}>{stream_btn_title}</button>
          <button onClick={toggleRecording}>{record_btn_title}</button>
        </div>
    );
};

const RecordAllControl = ({ctrl_state, update_ctrl_state}) => {
    // should only allow start if no one is recording
    // should allow stop if at least one is recording.
    let any_recording = false;
        
    for (const src_state of Object.values(ctrl_state["img_srcs"])) {
        if (src_state["writing"]) {
            any_recording = true;
            break;
        }
    }

    const rec_btn_title = any_recording ? "Stop Recording" : "Start Recording";
    
    const toggleRecording = (e) => {

        if (any_recording) {
            fetch("http://localhost:5000/video_writer/all/stop")
                .then(update_ctrl_state);
        }
        else {
            fetch("http://localhost:5000/video_writer/all/start")
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
    const [imageSources, setImageSources] = React.useState([]);
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

        fetch("http://localhost:5000/list_image_sources")
            .then(res => res.json())
            .then(
                (res) => {
                    setImageSources(res);
                },
                (error) => {
                    setError([error.toString()]);
                }
            );

        update_ctrl_state();
        //setInterval(update_ctrl_state, 1000);
    }, []);

    if (ctrlState === null)
        return null;
    
    const imgSrcViews = imageSources.map((srcId, srcIdx) => {
        return <ImageSourceView srcId={srcId}
                                srcIdx={srcIdx}
                                stream_width={320}
                                stream_height={240}
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
