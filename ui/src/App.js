import './App.css';
import React from 'react';
import {ExperimentView} from './experiment_view.js';
import {StreamGroupView} from './stream_view.js';
import {StateView} from './state_view.js';
import {VideoRecordView} from './video_record_view.js';
import {SocketContext} from './socket.js';
import {LogView} from './log_view.js';
import {api_url} from './config.js';

const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);
    const [sourcesConfig, setSourcesConfig] = React.useState(null);

    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback((old_state, new_state) => {
	setCtrlState(new_state);
    }, []);

    const handle_disconnect = React.useCallback(() => setCtrlState(null), []);
    
    React.useEffect(() => {
	socket.on("state", handle_new_state);
	socket.on("disconnect", handle_disconnect);

	fetch(api_url + "/config/image_sources")
	    .then(res => res.json())
	    .then(json => setSourcesConfig(json));
    }, [handle_disconnect, handle_new_state, socket]);

    if (ctrlState===null)
	return (
	    <div className="App">
		<p>Waiting for API...</p>
	    </div>
	);
    
    return (
        <div className="App">
	  <ExperimentView ctrl_state={ctrlState}/>
	  <VideoRecordView ctrl_state={ctrlState} />
	  <StreamGroupView image_sources={Object.keys(ctrlState.image_sources)}
			   sources_config={sourcesConfig}/>
	  <StateView ctrl_state={ctrlState} />
          <LogView />
        </div>
    );
};

export default App;
