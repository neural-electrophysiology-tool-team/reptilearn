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

const App = () => {
    const [ctrlState, setCtrlState] = React.useState(null);
    const [sourcesConfig, setSourcesConfig] = React.useState(null);

    const socket = React.useContext(SocketContext);
    
    const handle_new_state = React.useCallback((old_state, new_state) => {
	setCtrlState(JSON.parse(new_state));
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

    const valid_image_sources = Object.keys(ctrlState.image_sources).filter(key => ctrlState.image_sources[key].acquiring);
    
    return (
	<div className="App">
          <ReflexContainer orientation="horizontal" windowResizeAware={true}>
            
            <ReflexElement>
              <ReflexContainer orientation="vertical" windowResizeAware={true}>    

                <ReflexElement flex={0.65}>
                  <ReflexContainer orientation="horizontal" windowResizeAware={true}>
                    <ReflexElement size={20} className="section_header" maxSize={20} minSize={20}>
                      <span className="title">ReptiLearn</span>
                    </ReflexElement>

                    <ReflexElement className="subsection_header" size={30} minSize={30} maxSize={30}>
                      	  <VideoRecordView ctrl_state={ctrlState} />
                    </ReflexElement>
		    
                    <ReflexElement className="component">
                    <StreamGroupView image_sources={valid_image_sources}
			             sources_config={sourcesConfig} />       
                    </ReflexElement>
             
                  </ReflexContainer>
                </ReflexElement>
                <ReflexSplitter/>

                <ReflexElement>
                  <ReflexContainer orientation="horizontal" windowResizeAware={true}>
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

            <ReflexElement className="component" minSize={60} flex="0.2">  
              <LogView/>
            </ReflexElement>                     
          </ReflexContainer>
	</div>
    );
};

export default App;
