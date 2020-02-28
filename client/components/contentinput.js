/*
 * micro
 * Copyright (C) 2018 micro contributors
 *
 * This program is free software: you can redistribute it and/or modify it under the terms of the
 * GNU Lesser General Public License as published by the Free Software Foundation, either version 3
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
 * even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along with this program.
 * If not, see <http://www.gnu.org/licenses/>.
 */

/** TODO. */

"use strict";

/**
 * TODO.
 */
micro.ContentInputElement = class extends HTMLElement {
    createdCallback() {
        console.log("CREATE TEXT ENTITY");
        this.appendChild(
            document.importNode(ui.querySelector("#micro-content-input-template").content,
                                true));
        this._urls = new Set();
        this._data = new micro.bind.Watchable({
            resource: null,

            remove: () => {
                console.log("REEEEMOOOVE");
                this._data.resource = null;
            },

            input: async (event) => {
                // TODO: works, but just selecting and then deselecting an URL will detect a new URL
                // good enough, or should be better?
                //console.log(this._urls);
                //if (this._data.resourceElem) {
                if (this._data.resource) {
                    return;
                }

                let textarea = event.target;
                let urls = micro.util.findURLs(textarea.value);
                if (textarea === document.activeElement) {
                    urls = urls.filter(u => textarea.selectionStart < u.from || textarea.selectionStart > u.to);
                }
                //console.log(urls);
                let newURL = urls.find(u => !this._urls.has(u.url));
                this._urls = new Set(urls.map(u => u.url));
                if (newURL) {
                    newURL = newURL.url;
                    console.log(newURL);
                    this._data.previewing = true;
                    let resource = null;
                    try {
                        resource = await micro.call("GET", `/api/previews/${newURL}`);
                    } catch (e) {
                        console.log("ERROR", e.error);
                        if (!(e instanceof micro.APIError && e.error.__type__ === "WebError")) {
                            throw e;
                        }
                    }
                    this._data.previewing = false;
                    console.log("ENTITY", resource);

                    if (resource) {
                        this._data.resource = resource;
                        // this._data.entity_url = newURL;
                    }
                }
                /*let newURL = urls.find(u =>
                    !this._urls.has(u.url) &&
                    !(document.activeElement && textarea.selectionStart >= u.from &&
                      textarea.selectionStart <= u.to));*/
            }
        });
        micro.bind.bind(this.children, this._data);

        let updateClass = () => {
            this.classList.toggle("micro-content-input-resource", this._data.resource);
            this.classList.toggle("micro-content-input-previewing", this._data.previewing);
        };
        this._data.watch("resource", updateClass);
        this._data.watch("previewing", updateClass);

        this._textarea = this.querySelector("textarea");
    }

    reset() {
        this._textarea.value = "";
        this._data.resource = null;
    }

    get name() {
        return this._textarea.name;
    }

    set name(value) {
        this._textarea.name = value;
    }

    get placeholder() {
        return this._textarea.placeholder;
    }

    set placeholder(value) {
        this._textarea.placeholder = value;
    }

    get valueAsObject() {
        return {text: this._textarea.value, resource: this._data.resource};
    }

    set valueAsObject(value) {
        this._textarea.value = value.text;
        this._data.resource = value.resource;
    }
};
document.registerElement("micro-content-input", micro.ContentInputElement);

    /*get value() {
        return {
            text: this._textarea.value,
            entity: this._data.entity_url
        };
    }

    set value(value) {
        this._textarea.value = value.text;
        this._data.entity_url = value.entity;
    }*/

        /*Object.defineProperty(this._textarea, "valueAsObject", {
            get: () => ({text: this._textarea.value, resource: this._data.resource}),

            set: value => {
                this._textarea.value = value.text;
                this._data.resource = value.resource;
            }
        });*/
