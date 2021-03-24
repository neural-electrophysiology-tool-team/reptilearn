import './App.css';
import 'semantic-ui-css/semantic.min.css';
import 'react-reflex/styles.css';

import React from 'react';
import {MainPanelView} from './main_panel_view.js';
import {SocketContext} from './socket.js';
import {api_url} from './config.js';
      
const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);
    const [sourcesConfig, setSourcesConfig] = React.useState(null);
    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback((old_state, new_state) => {
	setCtrlState(JSON.parse(new_state));
    }, []);

    const handle_disconnect = React.useCallback(() => setCtrlState(null), []);

    window.onbeforeunload = () => true;    

    React.useEffect(() => {
	socket.on("state", handle_new_state);
	socket.on("disconnect", handle_disconnect);
        socket.on("connect", () => {
	    fetch(api_url + "/config/image_sources")
	        .then(res => res.json())
	        .then(json => setSourcesConfig(json));
        });
    }, [handle_disconnect, handle_new_state, socket]);

    if (ctrlState == null || sourcesConfig == null)
	return (
	    <div className="App">
		<p>Loading...</p>
	    </div>
	);
    
    return (
        <div className="App">
          <MainPanelView ctrl_state={ctrlState}                         
			 sources_config={sourcesConfig} />
        </div>
    );   
};

export default App;
