import './App.css';
import 'react-reflex/styles.css';

import React from 'react';
import { MainPanelView } from './main_panel_view.js';
import { SocketContext } from './socket.js';
import { api_url } from './config.js';
import 'semantic-ui-css/semantic.min.css';

const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);
    const [videoConfig, setVideoConfig] = React.useState(null);
    
    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback(new_state => {
	setCtrlState(JSON.parse(new_state));
    }, []);

    const handle_disconnect = React.useCallback(() => setCtrlState(null), []);

    // Display confirmation dialog before unloading page.
    // window.onbeforeunload = () => true;    

    React.useEffect(() => {
	socket.on("state", handle_new_state);
	socket.on("disconnect", handle_disconnect);
        socket.on("connect", () => {
        });
    }, [handle_disconnect, handle_new_state, socket]);

    const fetch_video_config = React.useCallback(() => {
        return fetch(api_url + '/video/get_config')
            .then((res) => res.json())
            .then((config) => setVideoConfig(config))
            .catch(err => {
		console.log(`Error while fetching video config: ${err}`);
		setTimeout(fetch_video_config, 5000);
	    });
    }, [setVideoConfig]);
    
    React.useEffect(() => {
        fetch_video_config();
    }, [fetch_video_config]);
    
    if (ctrlState === null || videoConfig === null)
	return (
	    <div className="App">
		<div style={{
			 position: 'absolute',
			 top: '50%',
			 left: '50%',
			 transform: 'translate(-50%, -50%)',
			 textAlign: 'center',
		     }}>
		    <div style={{ fontSize: '5rem', marginBottom: '2rem', display: 'inline-block'}}>ReptiLearn</div>
		    <div>Waiting for connection...</div>
		</div>
	    </div>
	);
    
    return (
        <div className="app">
          <MainPanelView ctrl_state={ctrlState} video_config={videoConfig} fetch_video_config={fetch_video_config}/>
        </div>
    );   
};

export default App;
