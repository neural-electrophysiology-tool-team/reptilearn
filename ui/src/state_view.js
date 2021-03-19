import React from 'react';
import ReactJson from 'react-json-view';

export const StateView = ({ctrl_state}) => {
    return (
	//	<div className="component flex_col">	
	<div className="pane-content">
	  <div className="section_header">
            <span className="title">State</span>
          </div>
	    <ReactJson src={ctrl_state} name={null} />
	</div>
    );
}
