import React from 'react';

export const VideoRecordView = ({ctrl_state}) => {
    let any_recording = false;
        
    for (const src_state of Object.values(ctrl_state["image_sources"])) {
        if (src_state["writing"]) {
            any_recording = true;
            break;
        }
    }

    if (ctrl_state == null)
	return null;
    
    const image_sources = Object.keys(ctrl_state.image_sources);
    const rec_btn_title = any_recording ? "Stop Recording" : "Start Recording";
    const ttl_btn_title = ctrl_state.video_recorder.ttl_trigger ? "Stop Trigger" : "Start Trigger";
    
    const toggle_recording = (e) => {
        if (any_recording) {
            fetch("http://localhost:5000/video_record/stop");
        }
        else {
            fetch("http://localhost:5000/video_record/start");
        }
    };

    const toggle_ttl_trigger = (e) => {
        if (ctrl_state.video_recorder.ttl_trigger) {
            fetch("http://localhost:5000/video_record/stop_trigger");
        }
        else {
            fetch("http://localhost:5000/video_record/start_trigger");
        }      
    };
    
    const src_changed = (e) => {
        const src_id = e.target.name;
        
        if (e.target.checked) {
            fetch(`http://localhost:5000/video_record/select_source/${src_id}`);
        }
        else {
            fetch(`http://localhost:5000/video_record/unselect_source/${src_id}`);
        }
    };
          
    const source_checkboxes = image_sources.map(src_id => {
        return (
            <span>
              <input type="checkbox"
                     onChange={src_changed}
                     name={src_id}
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
