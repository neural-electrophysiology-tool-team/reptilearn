import React from 'react';
import { Icon } from 'semantic-ui-react';
import ReactJson from 'react-json-view';
import {Selector} from './components.js';
import {api_url} from './config.js';

export const BlocksView = ({is_running, cur_block, params, blocks, set_blocks}) => {
    const reset_block = (idx) => {
        fetch(api_url + `/session/blocks/update/${idx}`, { method: "POST" });
    };
    
    const remove_block = (idx) => {
        const bs = [...blocks];
        bs.splice(idx, 1);
        set_blocks(bs);
    };
    
    const add_block_param = (idx, key) => {
        const bs = [...blocks];

        if (params[key] === undefined)
            bs[idx][key] = null;
        else
            bs[idx][key] = params[key];
        set_blocks(bs);
    };

    const shift_block_up = (idx) => {
        const bs = [...blocks];
        const b = blocks[idx];
        bs.splice(idx, 1);
        bs.splice(idx - 1, 0, b);
        set_blocks(bs);
    };

    const shift_block_down = (idx) => {
        const bs = [...blocks];
        const b = blocks[idx];
        bs.splice(idx, 1);
        bs.splice(idx + 1, 0, b);
        set_blocks(bs);
    };

    const duplicate_block = (idx) => {
        const bs = [...blocks];
        const b = {...blocks[idx]};
        bs.splice(idx + 1, 0, b);
        set_blocks(bs);
    };

    const insert_block_after = (idx) => {
        const bs = [...blocks];
        bs.splice(idx + 1, 0, {});
        set_blocks(bs);
    };

    /*
    const insert_block_before = (idx) => {
        const bs = [...blocks];
        bs.splice(idx - 1, 0, {});
        set_blocks(bs);
    };
    */
    
    const on_block_changed = (e, block_idx) => {
        const bs = blocks.map(s => ({...s}));
        bs[block_idx] = e.updated_src;
        set_blocks(bs);
    };

    const block_override_selector = (block_idx) => {
        const block = blocks[block_idx];
        let options = ["Override", ...Object.keys(params).filter(
            key => block[key] === undefined
        )];
	
        if (!options.includes("num_trials"))
            options.push("num_trials");
        
        return <Selector options={options}
                         selected={options[0]}
                         disabled={is_running}
                         on_select={key => add_block_param(block_idx, key)}
               />;
    };

    if (!blocks)
        return null;
    
    const block_divs = blocks.map((block, idx) => (
        <div key={idx}>
          <div className="subsection_header"
               style={{backgroundColor: cur_block === idx ? "#30914a" : "white"}}>
	    <span className="title">
              <button onClick={(e) => remove_block(idx)}
                      disabled={is_running || blocks.length === 1}
                      title="Remove block">
		<Icon name="x" size="small" fitted/>
              </button>
              Block {idx+1}
              <button onClick={(e) => shift_block_up(idx)}
                      disabled={is_running || idx === 0}
                      title="Shift up">
		<Icon name="angle up" size="small" fitted/>
              </button>
              <button onClick={(e) => shift_block_down(idx)}
                      disabled={is_running || idx === blocks.length-1}
                      title="Shift down">
		<Icon name="angle down" size="small" fitted />
              </button>                    
              <button onClick={(e) => duplicate_block(idx)}
                      disabled={is_running}
                      title="Duplicate">
		<Icon name="clone" size="small" fitted />
              </button>
              <button onClick={(e) => insert_block_after(idx)}
                      disabled={is_running}
                      title="Insert below">
		<Icon name="add" size="small" fitted/>
              </button>                                        
	    </span>
	    {block_override_selector(idx)}
	    <button onClick={(e) => reset_block(idx)}
		    disabled={is_running}
		    title="Reset block">
	      <Icon name="undo" size="small" fitted/>
	    </button>
          </div>
          <div className="subsection">
	    <ReactJson src={blocks[idx]}
                       name={null}
                       onEdit={is_running ? undefined : (e) => on_block_changed(e, idx)}
                       onAdd={is_running ? undefined : (e) => on_block_changed(e, idx)}
                       onDelete={is_running ? undefined : (e) => on_block_changed(e,idx)}/>                 
          </div>
        </div>
    ));
    return (
        <div style={{overflow: "hidden"}}>
          {block_divs}           
        </div>
    );
};
