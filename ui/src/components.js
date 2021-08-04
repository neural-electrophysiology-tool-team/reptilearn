import React from 'react';

export const Selector = ({options, selected, on_select, disabled, disabled_options, name, className}) => {
    if (!disabled_options)
	disabled_options = [];

    const option_items = options.map(
        (val, idx) => {
            return (
                <option key={idx}
			value={idx}
			disabled={disabled_options.indexOf(val) !== -1}>
		    {val}
		</option>
            );
        }
    );

    const on_change = (e) => {
        const i = parseInt(e.target.value);
	if (on_select)
            on_select(options[i], i);
    };
                            
    return <select onChange={on_change}
		   disabled={disabled}
		   value={selected}             
		   name={name}
                   className={className}>{option_items}</select>;
};
