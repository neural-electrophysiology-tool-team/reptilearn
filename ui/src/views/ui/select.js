export const RLSelect = ({ options, values, selected, setSelected, disabled, disabledOptions, name, className }) => {
    if (!disabledOptions)
        disabledOptions = [];

    const option_items = options.map(
        (val, idx) => {
            return (
                <option key={idx}
                    value={values? values[idx] : idx}
                    disabled={disabledOptions.indexOf(val) !== -1}>
                    {val}
                </option>
            );
        }
    );

    const on_change = (e) => {
        const i = parseInt(e.target.value);

        if (setSelected)
            setSelected(values ? e.target.value : options[i], values ? undefined : i);
    };

    return (
        <select onChange={on_change}
            disabled={disabled}
            value={selected}
            name={name}
            className={className}>{option_items}
        </select>
    );
};
