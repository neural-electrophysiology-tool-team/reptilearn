/**
 * Author: Tal Eisenberg (2023)
 */

export const get_configuration = () => {
    try {
        const ser = localStorage.getItem("configuration");
        return JSON.parse(ser);
    } catch (e) {
        console.error("Error parsing configuration from local storage: ", e);
        return null;
    }
}

export const set_configuration = (config) => {
    localStorage.setItem("configuration", JSON.stringify(config));
}

export const location_for_canvas_id = (canvas_id) => window.location.origin + '/' + canvas_id;
