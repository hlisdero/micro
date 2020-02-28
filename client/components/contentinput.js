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
micro.TextEntityInput = class extends HTMLElement {
    createdCallback() {
        console.log("CREATE TEXT ENTITY");
        this.appendChild(
            document.importNode(ui.querySelector("#micro-text-entity-input-template").content,
                                true));
        this._urls = new Set();
        this._data = new micro.bind.Watchable({
            entity: null,

            remove: () => {
                console.log("REEEEMOOOVE");
                this._data.entity = null;
            },

            input: async (event) => {
                // TODO: works, but just selecting and then deselecting an URL will detect a new URL
                // good enough, or should be better?
                //console.log(this._urls);
                if (this._data.entityElem) {
                    return;
                }

                let textarea = event.target;
                let urls = micro.util.findURLs(textarea.value);
                if (textarea == document.activeElement) {
                    urls = urls.filter(u => textarea.selectionStart < u.from || textarea.selectionStart > u.to);
                }
                //console.log(urls);
                let newURL = urls.find(u => !this._urls.has(u.url));
                this._urls = new Set(urls.map(u => u.url));
                if (newURL) {
                    newURL = newURL.url;
                    console.log(newURL);
                    this._data.previewing = true;
                    let entity = null;
                    try {
                        entity = await micro.call("GET", `/api/previews/${newURL}`);
                    } catch (e) {
                        console.log("ERROR", e.error);
                        if (!(e instanceof micro.APIError && e.error.__type__ === "WebError")) {
                            throw e;
                        }
                    }
                    this._data.previewing = false;
                    console.log("ENTITY", entity);

                    if (entity) {
                        this._data.entity = entity;
                        this._data.entity_url = newURL;
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
            this.classList.toggle("micro-text-entity-input-entity", this._data.entity);
            this.classList.toggle("micro-text-entity-input-previewing", this._data.previewing);
        };
        this._data.watch("entity", updateClass);
        this._data.watch("previewing", updateClass);

        this._textarea = this.querySelector("textarea");
    }

    get value() {
        return {
            text: this._textarea.value,
            entity: this._data.entity_url
        };
    }

    set value(value) {
        this._textarea.value = value.text;
        this._data.entity_url = value.entity;
    }

    reset() {
        this.value = {text: "", entity: null};
    }
};
document.registerElement("micro-text-entity-input", micro.TextEntityInput);
