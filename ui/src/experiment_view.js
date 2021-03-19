import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view';
import {api_url} from './config.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';

const assign_keep_old = (o, n) => {
    if (o === null || o === undefined)
        return n;
    if (n === null || n === undefined)
        return o;                        
    Object.keys(n).forEach(param => {
	if (o[param] !== undefined)
	    n[param] = o[param];
    });
    return n;
};

export const ExperimentView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [experimentParams, setExperimentParams] = React.useState({});
    const [experimentBlocks, setExperimentBlocks] = React.useState([]);
    const [defaultParams, setDefaultParams] = React.useState(null);
    const [defaultBlocks, setDefaultBlocks] = React.useState(null);
    const [error, setError] = React.useState(null);
    
    const exp_url = api_url + "/experiment";

    const update_defaults = (override_blocks) => {
	fetch(exp_url + "/default_params")
	    .then(res => res.json())
	    .then(new_defaults => {
                if (new_defaults === null || new_defaults === undefined) {
                    setDefaultParams(null);
                    setDefaultBlocks(null);
                }
                else {                
                    const new_default_params = new_defaults.params === undefined ?
                          null : new_defaults.params;
                    const new_default_blocks = new_defaults.blocks === undefined ?
                          null : new_defaults.blocks;
                    setDefaultParams(new_default_params);
                    setDefaultBlocks(new_default_blocks);
                    merge_params(new_default_params);
                    if (override_blocks || new_default_blocks.length === experimentBlocks.length)
                        merge_all_blocks(new_default_blocks);
                }
            });
    };

    const merge_params = (new_defaults) => {
        setExperimentParams(assign_keep_old(experimentParams, new_defaults));
    };

    const merge_all_blocks = (new_defaults) => {
        const blocks = [];
        new_defaults.forEach((new_block, i) => {
            blocks.push(merge_block(new_block, i));
        });
        setExperimentBlocks(blocks);
    };

    const merge_block = (new_defaults, block_idx) => {
        const new_default_block = {...new_defaults};
        const experiment_block = (experimentBlocks.length > block_idx) ?
              {...experimentBlocks[block_idx]} : null;

        return assign_keep_old(experiment_block, new_default_block);        
    };
    
    const reset_params = () => {
        setExperimentParams(defaultParams);
    };

    const reset_block = (block_idx) => {
        const blocks = [...experimentBlocks];

        if (block_idx < defaultBlocks.length)
            blocks[block_idx] = defaultBlocks[block_idx];
        else
            blocks[block_idx] = {};
        setExperimentBlocks(blocks);
    };

    const reset_all_blocks = () => {
        setExperimentBlocks(defaultBlocks);
    };
    
    const remove_block = (block_idx) => {
        const blocks = [...experimentBlocks];
        blocks.splice(block_idx, 1);
        setExperimentBlocks(blocks);
    };

    const add_block = () => {
        const blocks = [...experimentBlocks];
        blocks.push({});
        setExperimentBlocks(blocks);
    };

    const add_block_param = (block_idx, key) => {
        const blocks = [...experimentBlocks];
        console.log(blocks, block_idx);
        blocks[block_idx][key] = experimentParams[key];
        setExperimentBlocks(blocks);
    };
    
    const set_experiment = exp_name => {
        if (is_running) {
            update_defaults(false);
            return;
        }
        
        const new_exp = exp_name !== ctrl_state.experiment.cur_experiment;
	if (new_exp) {
	    setExperimentParams({});
            setExperimentBlocks([]);
	}
	
	fetch(exp_url + `/set/${exp_name}`)
	    .then((res) => update_defaults(new_exp));
    };

    const refresh_experiment_list = (e) => {
        fetch(exp_url + "/refresh_list")
            .then(res => res.json())
            .then(
                res => setExperimentList(res),
                error => setError(error.toString()));
    };
    
    const run_experiment = () => {
	fetch(exp_url + "/run", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify({"params": experimentParams,
				  "blocks": experimentBlocks})
	}).then(res => {
	    if (!res.ok)
		res.text().then(json => console.log(json));
	});
	
    };

    const end_experiment = () => {
	fetch(exp_url + "/end")
	    .then(res => console.log(res));
    };

    const on_params_changed = (e) => {
	setExperimentParams(e.updated_src);
    };

    const on_block_changed = (e, block_idx) => {
        const blocks = experimentBlocks.map(s => ({...s}));
        blocks[block_idx] = e.updated_src;
        setExperimentBlocks(blocks);
    };

    const next_block = () => {
        fetch(exp_url + "/next_block");
    };

    const next_trial = () => {
        fetch(exp_url + "/next_trial");
    };
    
    React.useEffect(() => {
	fetch(exp_url + "/list")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
                    if (ctrl_state !== null && ctrl_state.experiment.cur_experiment !== null
                       && ctrl_state.experiment.cur_experiment !== undefined) {
                        set_experiment(ctrl_state.experiment.cur_experiment);
                    }
                },
                (error) => {
                    setError(error.toString());
                }
            );               
    }, []);

    
    if (!ctrl_state)
	return null;

    const cur_exp_name = ctrl_state.experiment.cur_experiment;
    const cur_exp_idx = experimentList.indexOf(cur_exp_name) + 1;
    const is_running = ctrl_state.experiment.is_running;
    
    const reload_btn = cur_exp_name ? (
	<button onClick={(e) => set_experiment(cur_exp_name)}
		disabled={is_running}>
	  Reload
	</button>)
                : null;
    
    const run_end_btn = is_running ?
          <button onClick={end_experiment}>End Experiment</button>
	  : <button onClick={run_experiment}>Run Experiment</button>;

    const run_state_element = !is_running ? null :
          <ReflexElement size={26} minSize={26} maxSize={26} className="subsection_header">
            <label>block:</label>
            <input type="text" readOnly value={ctrl_state.experiment.cur_block} size="2"/>
            <button onClick={next_block}>+</button>
            <label> trial:</label>
            <input type="text" readOnly value={ctrl_state.experiment.cur_trial} size="2"/>
            <button onClick={next_trial}>+</button>
          </ReflexElement>;

    const params_div = experimentParams !== null ?
          (
          <React.Fragment>
              <div className="subsection_header">
                <span className="title">Parameters</span>
                <button onClick={reset_params} disabled={is_running}>Reset</button>
              </div>
              <div className="subsection">
	        <ReactJson src={experimentParams}
		           name={null}
		           onEdit={on_params_changed}
		           onAdd={on_params_changed}
                           onDelete={on_params_changed}
	        />
              </div>
          </React.Fragment>

          ) : null;

    const block_override_selector = (block_idx) => {
        const block = experimentBlocks[block_idx];
        const options = ["Override", ...Object.keys(experimentParams).filter(
            key => block[key] === undefined
        )];
        return <Selector options={options}
                         selected={options[0]}
                         disabled={is_running}
                         on_select={key => add_block_param(block_idx, key)}
               />;
    };
    
    const block_divs = experimentBlocks !== null ?
          experimentBlocks.map((block, idx) => (
              <div key={idx}>
                <div className="subsection_header">
                  <span className="title">
                    <button onClick={(e) => remove_block(idx)} disabled={is_running}>x</button>
                    
                    Block {idx}:
                  </span>
                  <button onClick={(e) => reset_block(idx)} disabled={is_running}>Reset</button>
                  {block_override_selector(idx)}
                </div>
                <div className="subsection">
                  <ReactJson src={experimentBlocks[idx]}
		             name={null}
		             onEdit={(e) => on_block_changed(e, idx)}
		             onAdd={(e) => on_block_changed(e, idx)}
                             onDelete={(e) => on_block_changed(e,idx)}
	          />                 
                </div>
              </div>
          )) : null;

    return (
        <ReflexContainer orientation="horizontal" key={Date()}>
          <ReflexElement size={26} minSize={26} maxSize={26} className="section_header">
            <span className="title">Experiment</span>
	    <Selector options={["None"].concat(experimentList)}
		      selected={cur_exp_idx}
		      on_select={set_experiment}
	              disabled={ctrl_state.experiment.is_running}/>
	    {reload_btn}
            <button onClick={refresh_experiment_list} disabled={is_running}>Refresh list</button>
            {run_end_btn}
          </ReflexElement>
          {run_state_element}
          <ReflexElement>
            {params_div}
            <div className="subsection_header">
              <span className="title">Blocks</span>
              <button onClick={add_block} disabled={is_running}>Add block</button>
              <button onClick={reset_all_blocks} disabled={is_running}>Reset blocks</button>
            </div>
            {block_divs}
          </ReflexElement>
        </ReflexContainer>       
    );
};
