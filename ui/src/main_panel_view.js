import React from 'react';
import {VideoRecordView} from './video_record_view.js';
import {StreamGroupView} from './stream_view.js';
import {ExperimentView} from './experiment_view.js';
import {ArenaControlView} from './arena_control_view.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';
import {LogView} from './log_view.js';

export const MainPanelView = ({ctrl_state, sources_config}) => {
    if (!sources_config) {
        return null;
    }

    const image_sources = Object.keys(ctrl_state.image_sources)
        .filter(key => ctrl_state.image_sources[key].acquiring);

    return (
        <ReflexContainer orientation="horizontal" windowResizeAware={true}>
          <ReflexElement minSize={22} maxSize={22} className="section_header"
                         style={{marginBottom: 0, overflow: "visible"}}>
            <span className="title">ReptiLearn</span>
            <VideoRecordView ctrl_state={ctrl_state}/>
            <ArenaControlView ctrl_state={ctrl_state}/>
          </ReflexElement>
          <ReflexElement>
            <ReflexContainer orientation="horizontal">          
              <ReflexElement>
                <ReflexContainer orientation="vertical" windowResizeAware={true}>
                  <ReflexElement flex={0.65} className="stream_group_view_container">
                    <StreamGroupView image_sources={image_sources}
                                     sources_config={sources_config}/>
                  </ReflexElement>
                  <ReflexSplitter/>
                  <ReflexElement minSize={400}>
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
};
