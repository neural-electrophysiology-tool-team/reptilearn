import React from 'react';
import ReactJson from 'react-json-view';
import { api_url } from '../config.js';
import { Bar } from './ui/bar.js';
import RLButton from './ui/button.js';
import { classNames } from './ui/common.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';

export const BlocksView = ({ is_running, cur_block, params, blocks, set_blocks }) => {
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
        bs[idx] = { ...bs[idx] };

        if (key in params) {
            bs[idx][key] = params[key];
        } else {
            bs[idx][key] = null;
        }

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
        const b = { ...blocks[idx] };
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
        const bs = blocks.map(s => ({ ...s }));
        bs[block_idx] = e.updated_src;
        set_blocks(bs);
    };

    const block_override_selector = (block_idx) => {
        const block = blocks[block_idx];
        let options = ["Override", ...Object.keys(params).filter(
            key => block[key] === undefined
        )];

        if (!options.includes("$num_trials"))
            options.push("$num_trials");
        if (!options.includes("$block_duration"))
            options.push("$block_duration")
        if (!options.includes("$trial_duration"))
            options.push("$trial_duration")
        if (!options.includes("$inter_trial_interval"))
            options.push("$inter_trial_interval")

        return <RLSimpleListbox options={RLListbox.simpleOptions(options)} selected={options[0]} setSelected={(key) => add_block_param(block_idx, key)}/>
    };

    if (!blocks)
        return null;

    const block_divs = blocks.map((block, idx) => (
        <div key={idx}>
            <Bar colors={classNames(cur_block === idx ? "bg-green-600" : "bg-gray-50", "border-gray-300")}>
                <RLButton.BarButton
                    onClick={(e) => remove_block(idx)}
                    disabled={is_running || blocks.length === 1}
                    title="Remove block"
                    icon="x"
                    iconClassName="h-[11px] w-[11px]"/>
                <div className="font-bold flex items-center px-1">Block {idx + 1}</div>
                <RLButton.BarButton
                    onClick={(e) => shift_block_up(idx)}
                    disabled={is_running || idx === 0}
                    title="Shift up" icon="angle-up" />
                <RLButton.BarButton
                    onClick={(e) => shift_block_down(idx)}
                    disabled={is_running || idx === blocks.length - 1}
                    title="Shift down" icon="angle-down" />
                <RLButton.BarButton 
                    onClick={(e) => duplicate_block(idx)}
                    disabled={is_running}
                    title="Duplicate"
                    icon="clone"/>
                <RLButton.BarButton
                    onClick={(e) => insert_block_after(idx)}
                    disabled={is_running}
                    title="Insert below"
                    iconClassName="h-[11px] w-[11px]"
                    icon="add"/>

                {block_override_selector(idx)}
                <RLButton.BarButton onClick={(e) => reset_block(idx)}
                    disabled={is_running}
                    title="Reset block" icon="undo"/>
            </Bar>
            <div className="pb-2  border-b-2 border-solid border-b-gray-200 h-fit">
                <ReactJson src={blocks[idx]}
                    name={null}
                    onEdit={is_running ? undefined : (e) => on_block_changed(e, idx)}
                    onAdd={is_running ? undefined : (e) => on_block_changed(e, idx)}
                    onDelete={is_running ? undefined : (e) => on_block_changed(e, idx)} />
            </div>
        </div>
    ));
    return (
        <div style={{ overflow: "hidden" }}>
            {block_divs}
        </div>
    );
};
