import React from 'react';
import {VideoRecordView} from './video_record_view.js';
import {StreamGroupView} from './stream_view.js';
import {ExperimentView} from './experiment_view.js';
import {ArenaControlView} from './arena_control_view.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';
import {LogView} from './log_view.js';

export const MainPanelView = ({ctrl_state, image_sources, sources_config}) => {
    if (image_sources === null || image_sources === undefined ||
        sources_config === null || sources_config === undefined) {
        return null;
    }

    return (
        <ReflexContainer orientation="horizontal">
          <ReflexElement
            minSize={22} maxSize={22} className="section_header" style={{marginBottom: 0, overflow: "visible"}}>
            <span className="title">ReptiLearn</span>
            <VideoRecordView ctrl_state={ctrl_state}/>
            <ArenaControlView ctrl_state={ctrl_state}/>
          </ReflexElement>
          <ReflexElement>
            <ReflexContainer orientation="horizontal">          
              <ReflexElement>
                <ReflexContainer orientation="vertical">    
                  <ReflexElement flex={0.65} style={{backgroundColor: "#555555"}}>
                    <StreamGroupView image_sources={image_sources}
                                     sources_config={sources_config}/>
                    
                  </ReflexElement>
                  
                  <ReflexSplitter/>
                  
                  <ReflexElement>
                    <ExperimentView ctrl_state={ctrl_state} />
                  </ReflexElement>
                </ReflexContainer>
              </ReflexElement>
              <ReflexSplitter/>
              <ReflexElement minSize={60} flex={0.2} style={{overflow: "hidden"}}>
                <LogView/>
              </ReflexElement>
            </ReflexContainer>            
          </ReflexElement>
        </ReflexContainer>
                    );
}
