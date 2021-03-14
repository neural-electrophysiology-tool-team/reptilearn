import './App.css';
import React from 'react';

import 'react-reflex/styles.css';

// then you can import the components
import {
    ReflexContainer,
    ReflexSplitter,
    ReflexElement
} from 'react-reflex';


import {ExperimentView} from './experiment_view.js';
import {StreamGroupView} from './stream_view.js';
import {StateView} from './state_view.js';
import {VideoRecordView} from './video_record_view.js';
import {SocketContext} from './socket.js';
import {LogView} from './log_view.js';
import {api_url} from './config.js';
import {layout} from './default_layout.js';

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
        socket.on("connect", () => {
	    fetch(api_url + "/config/image_sources")
	        .then(res => res.json())
	        .then(json => setSourcesConfig(json));
        });
    }, [handle_disconnect, handle_new_state, socket]);

    if (ctrlState===null || sourcesConfig===null)
	return (
	    <div className="App">
		<p>Waiting for API...</p>
	    </div>
	);

    return (
	<div className="App">
          <ReflexContainer orientation="horizontal">
            <ReflexElement>
              <ReflexContainer orientation="vertical">                

                <ReflexElement className="component" flex="0.65">
                  <StreamGroupView image_sources={Object.keys(ctrlState.image_sources)}
			           sources_config={sourcesConfig} />

                </ReflexElement>
                <ReflexSplitter/>

                <ReflexElement>
                  <ReflexContainer orientation="horizontal">
                    <ReflexElement className="component" flex="0.15">
                      	  <VideoRecordView ctrl_state={ctrlState} />
                    </ReflexElement>
                    
                    <ReflexElement className="component">
                      <ExperimentView ctrl_state={ctrlState}/>                  
                    </ReflexElement>
                    
                    <ReflexSplitter/>
                    
                    <ReflexElement className="component">  
                      <StateView ctrl_state={ctrlState}/>                 
                    </ReflexElement>

                  </ReflexContainer>
                </ReflexElement>
                
              </ReflexContainer>
            </ReflexElement>

            <ReflexSplitter/>

            <ReflexElement className="component" minSize="60" flex="0.2">  
              <LogView/>
            </ReflexElement>                     
          </ReflexContainer>
	</div>
    );
    /*
    return (
        <div className="App">
	  <ExperimentView ctrl_state={ctrlState}/>
          <div className="flex_box">
	    <StateView ctrl_state={ctrlState}/>
            <LogView/>
          </div>
        </div>
    );*/
};

export default App;
