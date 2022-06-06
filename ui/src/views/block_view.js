import React from 'react';
import { RLJSONEditor } from './ui/json_edit.js';
import { useSelector } from 'react-redux';

import { api_url } from '../config.js';
import { Bar } from './ui/bar.js';
import RLButton from './ui/button.js';
import { classNames } from './ui/common.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';


export const BlockView = ({ idx }) => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);

    const session = ctrl_state?.session;
    const is_running = session?.is_running;
    const params = session?.params;
    const blocks = session?.blocks;    
    const cur_block = session?.cur_block;

    const reset_block = () => {
        fetch(api_url + `/session/blocks/update/${idx}`, { method: "POST" });
    };

    const set_blocks = (blocks) => {
        fetch(api_url + "/session/blocks/update", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(blocks)
        });
    };

    const remove_block = () => {
        const bs = [...blocks];
        bs.splice(idx, 1);
        set_blocks(bs);
    };

    const add_block_param = (key) => {
        const bs = [...blocks];
        bs[idx] = { ...bs[idx] };

        if (key in params) {
            bs[idx][key] = params[key];
        } else {
            bs[idx][key] = null;
        }

        set_blocks(bs);
    };

    const shift_block_up = () => {
        const bs = [...blocks];
        const b = blocks[idx];
        bs.splice(idx, 1);
        bs.splice(idx - 1, 0, b);
        set_blocks(bs);
    };

    const shift_block_down = () => {
        const bs = [...blocks];
        const b = blocks[idx];
        bs.splice(idx, 1);
        bs.splice(idx + 1, 0, b);
        set_blocks(bs);
    };

    const duplicate_block = () => {
        const bs = [...blocks];
        const b = { ...blocks[idx] };
        bs.splice(idx + 1, 0, b);
        set_blocks(bs);
    };

    const insert_block_after = () => {
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

    const on_block_changed = (updatedContent, block_idx) => {
        const bs = blocks.map(s => ({ ...s }));
        bs[block_idx] = updatedContent.json;
        set_blocks(bs);
    };

    const block_override_selector = (idx) => {
        const block = blocks[idx];
        let options = Object.keys(params).filter(key => block[key] === undefined);

        if (!options.includes("$num_trials"))
            options.push("$num_trials");
        if (!options.includes("$block_duration"))
            options.push("$block_duration")
        if (!options.includes("$trial_duration"))
            options.push("$trial_duration")
        if (!options.includes("$inter_trial_interval"))
            options.push("$inter_trial_interval")

        return <RLSimpleListbox
            placeholder="Override"
            options={RLListbox.valueOnlyOptions(options)}
            selected={null}
            setSelected={(key) => add_block_param(key)}
            checked={false} />
    };

    if (!blocks)
        return null;

    return (
        <div key={idx} className="h-full flex flex-col">
            <Bar colors={classNames((cur_block === idx && session?.blocks?.length > 1) ? "bg-green-600" : "bg-gray-200")} border="none">
                <RLButton.BarButton
                    onClick={(e) => remove_block(idx)}
                    disabled={is_running || blocks.length === 1}
                    title="Remove block"
                    icon="xmark"/>
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
                    icon="add"/>

                {block_override_selector(idx)}
                <RLButton.BarButton onClick={(e) => reset_block(idx)}
                    disabled={is_running}
                    title="Reset block" icon="undo"/>
            </Bar>
            <RLJSONEditor
                content={{ json: blocks[idx] }}
                onChange={(updatedContent) => on_block_changed(updatedContent, idx)}
                className="h-[150px] overflow-y-auto flex flex-grow"
                readOnly={is_running}
                mainMenuBar={false}
                navigationBar={false}/>
        </div>
    );
};
