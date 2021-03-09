import React from 'react';

export const Selector = ({options, selected, on_select}) => {
    const option_items = options.map(
        (val, idx) => {
            if (idx == selected) {
                return (
                    <option key={idx} value={idx} selected>{val}</option>
                );                
            }
            else {
                return (
                    <option key={idx} value={idx}>{val}</option>
                );
            }
        }
    );

    const on_change = (e) => {
        const i = e.target.value;
        on_select(options[i], i);
    };
                            
    return <select onChange={on_change}>{option_items}</select>;
};
