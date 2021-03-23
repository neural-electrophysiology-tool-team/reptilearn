import React from 'react';
import {api_url} from './config.js';
import { Dropdown } from 'semantic-ui-react';
import { Icon } from 'semantic-ui-react';

export const VideoRecordView = ({ctrl_state}) => {
    const prefix_input_ref = React.useRef();
    
    if (ctrl_state == null)
	return null;

    const is_recording = ctrl_state.video_record.is_recording;
    const image_sources = Object.keys(ctrl_state.image_sources);
    const rec_btn_icon = is_recording ? "stop circle" : "circle";
    const ttl_trigger_state = ctrl_state.video_record.ttl_trigger;
    const ttl_btn_title = ttl_trigger_state ? "Stop Trigger" : "Start Trigger";
    const toggle_recording = (e) => {
        if (is_recording) {
            fetch(api_url + "/video_record/stop");
        }
        else {
            const prefix = prefix_input_ref.current.value;
            fetch(api_url + `/video_record/set_prefix/${prefix}`)
                .then(res => fetch(api_url + "/video_record/start"),
                      error => console.log("error"));
        }
    };

    const toggle_ttl_trigger = (e) => {
        if (ctrl_state.video_record.ttl_trigger) {
            fetch(api_url + "/video_record/stop_trigger");
        }
        else {
            fetch(api_url + "/video_record/start_trigger");
        }      
    };
    
    const src_changed = (src_id) => {
        if (ctrl_state.video_record.selected_sources.indexOf(src_id) === -1) {
            fetch(api_url + `/video_record/select_source/${src_id}`);
        }
        else {
            fetch(api_url + `/video_record/unselect_source/${src_id}`);
        }
    };

    const select_sources = (() => {
        const items = image_sources.map(src_id => {
            const selected = ctrl_state.video_record.selected_sources.indexOf(src_id) !== -1;
            return <Dropdown.Item text={src_id}
                                  icon={selected ? "check circle outline" : "circle outline"}
                                  onClick={() => src_changed(src_id)}
                                  key={src_id}/>;
        });
        return (
            <Dropdown text='Record Sources' disabled={is_recording}>
              <Dropdown.Menu>
                {items}
              </Dropdown.Menu>
            </Dropdown>
        );
    })();

    return (
        <span className="video_record_view">
          <input type="text"
                 name="prefix_input"
                 placeholder="video name"
                 ref={prefix_input_ref}
                 disabled={is_recording}
          />
          <button onClick={toggle_recording}><Icon size="small" fitted name={rec_btn_icon}/></button>
          <button onClick={toggle_ttl_trigger}>{ttl_btn_title}</button>
          <button disabled={is_recording}>
            {select_sources}
          </button>
        </span>
    );
};
