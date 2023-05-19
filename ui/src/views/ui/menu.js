import React from 'react';
import { Menu } from '@headlessui/react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { Float } from '@headlessui-float/react';
import { classNames, styles } from './common';

const RLMenu = ({ children, align, title, button, className }) => {
    return (
        <Menu>
            <Float
                tailwindcssOriginClass
                portal="#portalTarget"
                placement={(align && align === 'right') ? "bottom-end" : "bottom-start"}
                offset={1}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95">
                <div>{button || <BarMenuButton title={title} showDropIcon />}</div>

                <Menu.Items className={classNames(
                    className,
                    "rounded-sm shadow-lg bg-white overflow-hidden overflow-y-auto whitespace-nowrap focus:outline-none max-h-[75vh]")}>

                    {children}
                </Menu.Items>
            </Float>
        </Menu>
    );
};

const ButtonItem = ({ disabled, children, onClick, ...props }) => (
    <Menu.Item {...props} as="div" onClick={!disabled && onClick}>
        {({ active }) => (
            <div className={classNames(
                "p-2 cursor-pointer",
                active && "bg-gray-200",
                disabled ? "text-gray-400" : "hover:bg-gray-200")}>

                {children}
            </div>
        )}
    </Menu.Item>
);

const SeparatorItem = () => (
    <Menu.Item as="div" className="h-[2px] border-gray-200 border-b-2"></Menu.Item>
);

const HeaderItem = ({ children, ...props }) => (
    <Menu.Item as="div" className="p-1 first:pt-2 text-slate-600" {...props}>{children}</Menu.Item>
);

const StaticItem = ({ children, ...props }) => (
    <Menu.Item as="div" className="p-2" {...props}>{children}</Menu.Item>
)

const BarMenuButton = ({ title, showDropIcon }) => (
    <Menu.Button className={classNames("align-middle rounded-[4px] inline-flex justify-center w-full border border-gray-300 px-4  bg-white text-sm font-medium text-gray-700 hover:bg-gray-200", styles.focusBorder)}>
        {title}
        {showDropIcon && <FontAwesomeIcon icon="caret-down" className='h-[14px] w-[14px] -mr-1 ml-2 my-auto' />}
    </Menu.Button>
);

const TopBarMenuButton = ({ title, ...props }) => (
    <Menu.Button {...props} className={classNames("flex items-center border border-gray-300 px-4 py-1 bg-white text-sm text-gray-700 hover:bg-gray-100", styles.focusBorder)}>
        {title}
        <FontAwesomeIcon icon="caret-down" className='h-[14px] w-[14px] -mr-1 ml-2 my-auto' />
    </Menu.Button>
);

RLMenu.ButtonItem = ButtonItem;
RLMenu.SeparatorItem = SeparatorItem;
RLMenu.HeaderItem = HeaderItem;
RLMenu.StaticItem = StaticItem;
RLMenu.TopBarMenuButton = TopBarMenuButton;
RLMenu.BarMenuButton = BarMenuButton;

export default RLMenu;