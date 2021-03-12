import React from 'react';
import {api_url} from './config.js';

export const VideoRecordView = ({ctrl_state}) => {
    if (ctrl_state == null)
	return null;

    const is_recording = ctrl_state.video_recorder.is_recording;
    const image_sources = Object.keys(ctrl_state.image_sources);
    const rec_btn_title = is_recording ? "Stop Recording" : "Start Recording";
    const ttl_btn_title = ctrl_state.video_recorder.ttl_trigger ? "Stop Trigger" : "Start Trigger";
    
    const toggle_recording = (e) => {
        if (is_recording) {
            fetch(api_url + "/video_record/stop");
        }
        else {
            fetch(api_url + "/video_record/start");
        }
    };

    const toggle_ttl_trigger = (e) => {
        if (ctrl_state.video_recorder.ttl_trigger) {
            fetch(api_url + "/video_record/stop_trigger");
        }
        else {
            fetch(api_url + "/video_record/start_trigger");
        }      
    };
    
    const src_changed = (e) => {
        const src_id = e.target.name;
        
        if (e.target.checked) {
            fetch(api_url + `/video_record/select_source/${src_id}`);
        }
        else {
            fetch(api_url + `/video_record/unselect_source/${src_id}`);
        }
    };
          
    const source_checkboxes = image_sources.map(src_id => {
        return (
            <span key={src_id}>
              <input type="checkbox"
                     onChange={src_changed}
                     name={src_id}
                     checked={ctrl_state.video_recorder.selected_sources.indexOf(src_id) !== -1}
              />
              {src_id}
            </span>
        );
    });
    
    return (
        <div className="component">
	  {source_checkboxes}
          <br/>
          <button onClick={toggle_recording}>{rec_btn_title}</button>
          <button onClick={toggle_ttl_trigger}>{ttl_btn_title}</button>
        </div>
    );
};
