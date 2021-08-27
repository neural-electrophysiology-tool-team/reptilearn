import React from 'react';
import { api_url } from './config.js';
import { Dropdown } from 'semantic-ui-react';

export const ActionsView = ({actions}) => {
    const run_action = (label) => {
        fetch(api_url + `/run_action/${label}`);
    };
    
    const action_items = actions.map(a => (
        <Dropdown.Item text={a}
                       key={a}
                       onClick={() => run_action(a)}
                       disabled={false}/>
    ));
    
    return (
        <button>
          <Dropdown text='Actions'>
            <Dropdown.Menu>
              {action_items}
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );
};
