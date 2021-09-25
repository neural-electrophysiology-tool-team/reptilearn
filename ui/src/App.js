import './App.css';
import 'semantic-ui-css/semantic.min.css';
import 'react-reflex/styles.css';

import React from 'react';
import { MainPanelView } from './main_panel_view.js';
import { SocketContext } from './socket.js';
      
const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);

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

    if (ctrlState == null)
	return (
	    <div className="App">
		<p>Loading...</p>
	    </div>
	);
    
    return (
        <div className="App">
          <MainPanelView ctrl_state={ctrlState}/>
        </div>
    );   
};

export default App;
