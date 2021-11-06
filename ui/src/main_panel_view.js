import React from 'react';
import { VideoRecordView } from './video_record_view.js';
import { StreamGroupView } from './stream_view.js';
import { ExperimentView } from './experiment_view.js';
import { ArenaControlView } from './arena_control_view.js';
import { SessionMenuView } from './session_menu_view.js';
import { ReflexContainer, ReflexSplitter, ReflexElement } from 'react-reflex';
import { LogView } from './log_view.js';
import { TasksView } from './tasks_view.js';
import { Menu } from 'semantic-ui-react';

export const MainPanelView = ({ctrl_state, video_config, fetch_video_config}) => {
    //const acquiring_image_sources = Object.keys(ctrl_state.image_sources)
    //    .filter(key => ctrl_state.image_sources[key].acquiring);
    return (
        <ReflexContainer orientation="horizontal" windowResizeAware={true}>
          <ReflexElement minSize={22} maxSize={22} className="section_header"
                         style={{marginBottom: 0, overflow: "visible"}}>
            <Menu size="small">
              <Menu.Item><span className="title">ReptiLearn</span></Menu.Item>
              <VideoRecordView ctrl_state={ctrl_state} video_config={video_config} fetch_video_config={fetch_video_config}/>
	      <TasksView />
              <ArenaControlView ctrl_state={ctrl_state}/>
              <SessionMenuView ctrl_state={ctrl_state}></SessionMenuView>
            </Menu>
          </ReflexElement>
          <ReflexElement>
            <ReflexContainer orientation="horizontal" windowResizeAware={true}>
              <ReflexElement>
                <ReflexContainer orientation="vertical" windowResizeAware={true}>
                  <ReflexElement flex={0.65} className="stream_group_view_container">
                    <StreamGroupView ctrl_state={ctrl_state} video_config={video_config}/>
                  </ReflexElement>
                  <ReflexSplitter/>
                  <ReflexElement minSize={400}>
                    <ExperimentView ctrl_state={ctrl_state} />
                  </ReflexElement>
                </ReflexContainer>
              </ReflexElement>
              <ReflexSplitter/>
              <ReflexElement minSize={26} flex={0.2} style={{overflow: "hidden"}}>
                <LogView/>
              </ReflexElement>
            </ReflexContainer>            
          </ReflexElement>
        </ReflexContainer>
    );
};
