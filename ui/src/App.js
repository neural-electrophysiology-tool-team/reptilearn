import './App.css';
import 'semantic-ui-css/semantic.min.css';
import 'react-reflex/styles.css';

import React from 'react';
import { MainPanelView } from './main_panel_view.js';
import { SocketContext } from './socket.js';
import { api_url } from './config.js';

const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);
    const [videoConfig, setVideoConfig] = React.useState(null);
    
    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback(new_state => {
	setCtrlState(JSON.parse(new_state));
    }, []);

    const handle_disconnect = React.useCallback(() => setCtrlState(null), []);

    window.onbeforeunload = () => true;    

    React.useEffect(() => {
	socket.on("state", handle_new_state);
	socket.on("disconnect", handle_disconnect);
        socket.on("connect", () => {
        });
    }, [handle_disconnect, handle_new_state, socket]);

    const fetch_video_config = () => {
        fetch(api_url + '/video/get_config')
            .then((res) => res.json())
            .then((config) => setVideoConfig(config));        
    };
    
    React.useEffect(() => {
        fetch_video_config();
    }, []);
    
    if (ctrlState === null || videoConfig === null)
	return (
	    <div className="App">
		<p>Loading...</p>
	    </div>
	);
    
    return (
        <div className="App">
          <MainPanelView ctrl_state={ctrlState} video_config={videoConfig} fetch_video_config={fetch_video_config}/>
        </div>
    );   
};

export default App;
