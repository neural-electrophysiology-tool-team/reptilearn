import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view';
import {api_url} from './config.js';

export const ExperimentView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [experimentParams, setExperimentParams] = React.useState({});
    const [experimentBlocks, setExperimentBlocks] = React.useState([]);
    const [error, setError] = React.useState(null);

    const exp_url = api_url + "/experiment";

    const update_params = (old_defaults) => {
	fetch(exp_url + "/default_params")
	    .then(res => res.json())
	    .then(new_defaults => {
                // THIS IS CRAZY....
                console.log("new", new_defaults);
		if (new_defaults === null || new_defaults === undefined) {
		    setExperimentParams(null);
		    setExperimentBlocks(null);
		}
		else {
                    if (old_defaults === null || old_defaults === undefined) {
                        if (new_defaults.params !== undefined)
                            setExperimentParams(new_defaults.params);
                        if (new_defaults.blocks !== undefined)
                            setExperimentBlocks(new_defaults.blocks);
                    }
                    else {
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
                        
		        const params = assign_keep_old(old_defaults.params, new_defaults.params);
		        setExperimentParams(params);
                    
		        const old_blocks = old_defaults.blocks;
		        const new_blocks = new_defaults.blocks;
                        
                        if (old_blocks !== null && old_blocks !== undefined) {
                            const blocks = [];
		            new_blocks.forEach((new_block, i) => {
			        if (i < old_blocks.length)
			            blocks.push(assign_keep_old(old_blocks[i], new_block));
			        else
			            blocks.push(new_block);			
		            });
                            setExperimentBlocks(blocks);
                        }
                        else {
                            setExperimentBlocks(new_blocks);
                        }
                    }
		}
	    });
    };

    const reset_params = () => {
        update_params({});
    };
    
    const set_experiment = exp_name => {
	if (exp_name !== ctrl_state.experiment.cur_experiment) {
	    setExperimentParams({});
	}
	
	fetch(exp_url + `/set/${exp_name}`)
	    .then((res) => update_params(experimentParams));
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

    React.useEffect(() => {
	fetch(exp_url + "/list")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
		    update_params(experimentParams);
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

    const reset_params_btn = experimentParams !== null ?
          <button onClick={reset_params} disabled={is_running}>Reset</button>
          : null;
    
    const params_div = experimentParams !== null ?
          (
              <div>
                <label>Parameters:</label>{reset_params_btn}
	        <ReactJson src={experimentParams}
		           name={null}
		           onEdit={on_params_changed}
		           onAdd={on_params_changed}
                           onDelete={on_params_changed}
	        />
              </div>
          ) : null;
                           
    return (
	<div className="pane-content">
          Experiment:
	  <Selector options={["None"].concat(experimentList)}
		    selected={cur_exp_idx}
		    on_select={set_experiment}
	            disabled={ctrl_state.experiment.is_running}/>
	  {reload_btn}
          <button onClick={refresh_experiment_list} disabled={is_running}>Refresh list...</button>
          {run_end_btn}
	  <br/>
	  {params_div}
	</div>
    );
};
