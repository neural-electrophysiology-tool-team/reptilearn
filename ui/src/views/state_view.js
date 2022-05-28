import React from "react";
import { useSelector } from "react-redux";
import { Bar } from "./ui/bar";

import { RLJsonEdit } from "./ui/json_edit";
import { RLListbox, RLSimpleListbox } from "./ui/list_box";

export const StateView = () => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);

    const [ctrlStatePath, setCtrlStatePath] = React.useState();
    const [statePath, setStatePath] = React.useState([]);

    const update_ctrl_state_path = () => {
        if (!statePath || statePath.length === 0) {
            setCtrlStatePath(ctrl_state);
            return;
        }

        let cur = ctrl_state;
        for (const key of statePath) {
            if (cur[key]) {
                cur = cur[key];
            }
            else {
                setCtrlStatePath({});
                return;
            }
        }

        setCtrlStatePath(cur);
    };

    const keys_for_path = (i) => {
        let cur = ctrl_state;
        for (const key of statePath) {
            if (i === 0)
                break;

            if (cur[key]) {
                cur = cur[key];
                i--;
            }
            else {
                return [];
            }
        }

        return Object.keys(cur)
            .filter(k => cur[k] instanceof Array || cur[k] instanceof Object);
    };

    React.useEffect(update_ctrl_state_path, [ctrl_state, statePath]);

    const state_path_select = (i) => {
        const on_change = (value) => {
            const state_path = [...statePath];

            if (!value) {
                setStatePath(statePath.slice(0, i));
                return null;
            }

            state_path[i] = value;
            setStatePath(state_path);
        };

        const opts = RLListbox.simpleOptions([undefined, ...keys_for_path(i)]);

        if (opts.length === 1)
            return null;

        return (
            <RLSimpleListbox
                placeholder="..."
                options={opts}
                selected={statePath[i]}
                setSelected={on_change}
                key={i} />
        );
    };

    return (
        <div className="h-full flex flex-col">
            <Bar title="State">
                {[
                    ...statePath.map((p, idx) => state_path_select(idx)),
                    state_path_select(statePath.length)
                ]}
            </Bar>
            <div className="overflow-y-scroll">
                <RLJsonEdit
                    src={ctrlStatePath}
                    name={null}
                    style={{ height: "auto" }}
                />
            </div>
        </div>
    );
}