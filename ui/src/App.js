import './App.css';
import {Selector} from './components.js';
import React from 'react';
import {ExperimentView} from './experiment_view.js';
import {StreamView} from './stream_view.js';
import {StateView} from './state_view.js';
import {SocketContext} from './socket.js';
/*
TODO:
- stop stream before switching source.
- ui obviously.
- add a no image source option (default)
- streaming toggle is not working properly
*/


const RecordAllControl = ({ctrl_state}) => {
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
        }
        else {
            fetch("http://localhost:5000/video_record/start")
        }
    };
    
    return (
        <div className="component">
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
    const [imageSources, setImageSources] = React.useState(null);

    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback((old_state, new_state) => {
	console.log("new state arrived!");
	setCtrlState(new_state);
	if (imageSources === null)
	    setImageSources(Object.keys(new_state.image_sources));
    }, []);
    
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

	socket.on("state", handle_new_state);
    }, []);

    if (ctrlState === null)
        return null;

    const stream_view = imageSources !== null && imageSources.length > 0 ?
	<StreamView image_sources={imageSources}
                    source_idx={0}
                    stream_width={640}
                    stream_height={480}
        />
	  : null;

    return (
        <div className="App">
            {apiMsg}<br/>
            {error}
	    <ExperimentView cur_experiment={ctrlState.experiment.cur_experiment}/>
	    <RecordAllControl ctrl_state={ctrlState} />
	    {stream_view}
	    <StateView ctrl_state={ctrlState} />
        </div>
    );
};

export default App;
