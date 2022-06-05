import React from "react";
import { Float } from '@headlessui-float/react';
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Listbox } from "@headlessui/react";
import { classNames, styles } from "./common";

const RLListbox = ({ value, onChange, multiple, children, header, className }) => (
    <Listbox as="div" value={value} onChange={onChange} multiple={multiple}>
        <Float
            placement="bottom-start"
            offset={1}
            portal="#portalTarget"
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0">

            <Listbox.Button className={classNames(
                "relative cursor-default rounded-[4px] p-px h-[22px] bg-white border border-gray-300 px-2 text-left flex flex-row items-center",
                className,
                styles.disabled,
                styles.focusBorder
            )}>
                <span className="flex flex-1">{header}</span>
                <FontAwesomeIcon icon="caret-down" className="pl-2 h-[14px] w-[14px]" />
            </Listbox.Button>

            <Listbox.Options className={classNames("absolute max-h-60 overflow-auto rounded-md bg-white shadow-lg ring-1 ring-gray-100 z-[200] focus:outline-none")}>
                {children}
            </Listbox.Options>
        </Float>
    </Listbox >
);


const Option = ({ value, children, disabled, className }) => (
    <Listbox.Option disabled={disabled} value={value} className={({ active }) => classNames(
        'relative cursor-default select-none py-2 px-4 whitespace-nowrap',
        active ? 'bg-amber-100 text-amber-900' : 'text-gray-900',
        className, 
        )}>

        {children}
    </Listbox.Option>
);

const SimpleOption = ({ value, label, title, disabled }) => (
    <Option disabled={disabled} value={value}>
        {({ selected }) => (
            <span className={`block truncate ${selected ? "font-medium" : "font-normal"}`} title={title || label}>{label}</span>
        )}
    </Option>
);

const CheckedOption = ({ value, label, title, disabled }) => (
    <Option disabled={disabled} value={value} className="pl-10">
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
    <Option disabled className={classNames("text-gray-700")}>
        {children}
    </Option>
);

const RLSimpleListbox = ({ placeholder, options, selected, setSelected, header, className, checked=true }) => (
    <RLListbox
        header={selected ? options.filter(({ value }) => value === selected)[0]?.label : placeholder}
        value={selected}
        onChange={setSelected}
        className={className}>
        {header && <HeaderOption>{header}</HeaderOption>}
        {options.map(({ label, value, key }) => (
            checked ? <CheckedOption label={label} value={value} key={key}/> : <SimpleOption label={label} value={value} key={key}/>
        ))}
    </RLListbox>
);

RLListbox.valueOnlyOptions = (opts) => opts.map((key) => ({ label: key, value: key, key: key || '' + key }));

RLListbox.Option = Option;
RLListbox.CheckedOption = CheckedOption;
RLListbox.SimpleOption = SimpleOption;
RLListbox.HeaderOption = HeaderOption;

export { RLListbox, RLSimpleListbox };