import React from "react";
import { Popover } from "@headlessui/react";
import { Float } from '@headlessui-float/react';

export const RLTooltip = ({ children, content, delay = 500 }) => {
    const [open, setOpen] = React.useState(false);
    const [timeoutId, setTimeoutId] = React.useState(null);

    const handleEnter = () => {
        const id = setTimeout(() => setOpen(true), delay);
        setTimeoutId(id);
    };

    const handleLeave = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        setOpen(false);
    };

    return (
        <Popover >
            <Float
                placement="bottom"
                offset={15}
                shift={6}
                flip={10}
                arrow
                portal
                show={open}
                enter="transition duration-200 ease-out"
                enterFrom="opacity-0 -translate-y-1"
                enterTo="opacity-100 translate-y-0"
                leave="transition duration-150 ease-in"
                leaveFrom="opacity-100 translate-y-0"
                leaveTo="opacity-0 -translate-y-1">

                <div className="h-full flex" onMouseEnter={handleEnter} onMouseLeave={handleLeave}>
                    {children}
                </div>

                <Popover.Panel static className="w-fit h-fit bg-gray-900 border border-gray-800 rounded-md focus:outline-none">
                    <Float.Arrow className="absolute bg-gray-900 w-5 h-5 rotate-45 border border-gray-800" />
                    <div className="relative h-full bg-gray-900 py-1 px-2 text-gray-50 rounded-md">{content}</div>
                </Popover.Panel>
            </Float>
        </Popover>
    );
};