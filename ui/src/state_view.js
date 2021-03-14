import React from 'react';
import ReactJson from 'react-json-view'

export const StateView = ({ctrl_state}) => {
    return (
	//	<div className="component flex_col">	
	<div className="pane-content">
	    State:<br/>
	    <ReactJson src={ctrl_state} name={null} />
	</div>
    );
}
