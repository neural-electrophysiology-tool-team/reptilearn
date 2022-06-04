import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Listbox, Transition } from "@headlessui/react";
import { classNames, styles } from "./common";

const RLListbox = ({ value, onChange, multiple, children, header, className }) => (
    <Listbox as="div" value={value} onChange={onChange} multiple={multiple}>
        <Listbox.Button className={classNames(
            "relative cursor-default rounded-[4px] p-px h-[22px] bg-white border border-gray-300 px-2 text-left flex flex-row items-center",
            className,
            styles.disabled,
            styles.focusBorder
        )}>
            <span className="flex flex-1">{header}</span>
            <FontAwesomeIcon icon="angle-down" className="pl-2"/>
        </Listbox.Button>
        <Transition
            as={React.Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0">

            <Listbox.Options className={classNames("absolute mt-1 max-h-60 overflow-auto rounded-md bg-white py-1 shadow-lg ring-1 ring-black z-[200] focus:outline-none")}>
                {children}
            </Listbox.Options>
        </Transition>
    </Listbox>
);


const Option = ({ value, children, disabled }) => (
    <Listbox.Option disabled={disabled} value={value} className={({ active }) =>
        `relative cursor-default select-none py-2 pl-10 pr-4 ${active ? 'bg-amber-100 text-amber-900' : 'text-gray-900'
        }`
    }>
        {children}
    </Listbox.Option>
);

const CheckedOption = ({ value, label, title, disabled }) => (
    <Option disabled={disabled} value={value}>
        {({ selected }) => (
            <>
                {selected ? (
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-600">
                        <FontAwesomeIcon icon="check" className="h-5 w-5" aria-hidden="true" />
                    </span>
                ) : null}
                <span className={`block truncate ${selected ? "font-medium" : "font-normal"}`} title={title || label}>{label}</span>
            </>
        )}
    </Option>
);

const HeaderOption = ({ children }) => (
    <Listbox.Option disabled className={classNames("relative cursor-default select-none py-2 pl-3 pr-4 text-gray-700")}>
        {children}
    </Listbox.Option>
);

const RLSimpleListbox = ({ placeholder, options, selected, setSelected, header, className }) => (
    <RLListbox
        header={selected ? options.filter(({ value }) => value === selected)[0]?.label : placeholder}
        value={selected}
        onChange={setSelected}
        className={className}>
        {header && <HeaderOption>{header}</HeaderOption>}
        {options.map(({ label, value, key }) => (
            <CheckedOption label={label} value={value} key={key} />
        ))}
    </RLListbox>
);

RLListbox.simpleOptions = (opts) => opts.map((key) => ({ label: key, value: key, key: key || '' + key }));

RLListbox.Option = Option;
RLListbox.CheckedOption = CheckedOption;
RLListbox.HeaderOption = HeaderOption;

export { RLListbox, RLSimpleListbox };