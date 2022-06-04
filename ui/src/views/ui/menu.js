import React from 'react';
import { Menu, Transition } from '@headlessui/react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { classNames, styles } from './common';

const RLMenu = ({ children, align, title, button }) => {
    return (
        <Menu as="div" className="relative inline-block text-left overflow-visible">
            {button || <BarMenuButton title={title} showDropIcon />}
            <Transition
                as={React.Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95">
                <Menu.Items className={classNames(
                    "origin-top-right absolute rounded-sm shadow-lg bg-white overflow-hidden whitespace-nowrap z-[200] focus:outline-none",
                    align && (align === 'right') ? 'right-0' : 'left-0')}>

                    {children}
                </Menu.Items>
            </Transition>
        </Menu>
    );
};

const ButtonItem = ({ disabled, children, ...props }) => (
    <Menu.Item {...props} as="div">
        {({ active }) => (
            <div className={classNames(
                active && "bg-gray-200", "px-2 py-1 cursor-pointer first:pt-2", 
                disabled ? "text-gray-400" : "hover:bg-gray-200")}>

                {children}
            </div>
        )}
    </Menu.Item>
);

const SeparatorItem = () => (
    <Menu.Item as="div" className="h-1 border-gray-200 border-b-2"></Menu.Item>
);

const HeaderItem = ({ children, ...props }) => (
    <Menu.Item as="div" className="p-1 first:pt-2" {...props}>{children}</Menu.Item>
);

const StaticItem = ({ children, ...props }) => (
    <Menu.Item as="div" className="p-1" {...props}>{children}</Menu.Item>
)

const BarMenuButton = ({ title, showDropIcon }) => (
    <Menu.Button className={classNames("align-middle rounded-[4px] inline-flex justify-center w-full border border-gray-300 px-4  bg-white text-sm font-medium text-gray-700 hover:bg-gray-200", styles.focusBorder)}>
        {title}
        {showDropIcon && <FontAwesomeIcon icon="angle-down" className='h-4 w-4 -mr-1 ml-2 my-auto' />}
    </Menu.Button>
);

const TopBarMenuButton = ({ title, ...props }) => (
    <Menu.Button {...props} className={classNames("flex items-center border border-gray-300 px-4 py-1 bg-white text-sm font-medium text-gray-700 hover:bg-gray-100", styles.focusBorder)}>
        {title}
        <FontAwesomeIcon icon="angle-down" className='h-4 w-4 -mr-1 ml-2 my-auto' />
    </Menu.Button>
);

RLMenu.ButtonItem = ButtonItem;
RLMenu.SeparatorItem = SeparatorItem;
RLMenu.HeaderItem = HeaderItem;
RLMenu.StaticItem = StaticItem;
RLMenu.TopBarMenuButton = TopBarMenuButton;
RLMenu.BarMenuButton = BarMenuButton;

export default RLMenu;