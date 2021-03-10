import './App.css';
import {Selector} from './components.js';
import React from 'react';
import {ExperimentView} from './experiment_view.js';
import {StreamView} from './stream_view.js';
import {StateView} from './state_view.js';
import {VideoRecordView} from './video_record_view.js';
import {SocketContext} from './socket.js';
/*
TODO:
- stop stream before switching source.
- ui obviously.
- add a no image source option (default)
- streaming toggle is not working properly
*/



const fetch_control_state = (on_fetch) => {
    return fetch("http://localhost:5000/state")
        .then(res => res.json());
};
                  
const App = () => {
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

    const handle_disconnect = React.useCallback(() => setCtrlState(null))
    
    React.useEffect(() => {
	socket.on("state", handle_new_state);
	socket.on("disconnect", handle_disconnect);
    }, []);

    if (ctrlState===null)
	return (
	    <div className="App">
		<p>Waiting for API...</p>
	    </div>
	);
    
    const stream_view = imageSources !== null && imageSources.length > 0 ?
	<StreamView image_sources={imageSources}
                    source_idx={0}
                    stream_width={640}
                    stream_height={480}
        />
	  : null;

    return (
        <div className="App">
            {error}
	    <ExperimentView ctrl_state={ctrlState}/>
	    <VideoRecordView ctrl_state={ctrlState} />
	    {stream_view}
	    <StateView ctrl_state={ctrlState} />
        </div>
    );
};

export default App;
