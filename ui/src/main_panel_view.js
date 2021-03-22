import React from 'react';
import {VideoRecordView} from './video_record_view.js';
import {StreamGroupView} from './stream_view.js';
import {ArenaControlView} from './arena_control_view.js';

export const MainPanelView = ({ctrl_state, image_sources, sources_config}) => {
    const stream_group_view = React.useRef();
    const [streamCount, setStreamCount] = React.useState(0);

    React.useEffect(() => {
        stream_group_view.current.on_remove_stream(setStreamCount);
    }, [stream_group_view]);
    
    const add_stream_click = (e) => {
        stream_group_view.current.add_stream();
        setStreamCount(streamCount + 1);
    };

    const disable_add_stream = streamCount === image_sources.length;
    
    return (
        <div>
          <div className="section_header">
            <span className="title">ReptiLearn</span>
            <button onClick={add_stream_click}
                    disabled={disable_add_stream}>
              Add Stream
            </button>
            <span className="placeholder"/>
            <VideoRecordView ctrl_state={ctrl_state}/>
            <ArenaControlView ctrl_state={ctrl_state}/>
          </div>
          <div>
            <StreamGroupView image_sources={image_sources}
			     sources_config={sources_config}
                             ref={stream_group_view}/>
          </div>
        </div>

    );
}
