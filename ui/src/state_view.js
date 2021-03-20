import React from 'react';
import ReactJson from 'react-json-view';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';

export const StateView = ({ctrl_state}) => {
    return (
        <React.Fragment>
          <ReflexElement className="section_header pane-content">
            <span className="title">State</span>
          </ReflexElement>
          <ReflexElement>
            <ReactJson src={ctrl_state} name={null} />
          </ReflexElement>
	</React.Fragment>
    );
}
