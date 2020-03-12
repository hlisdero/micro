
                    <div class="listling-item-content-input micro-input-wrapper" data-resource="item.resource">
                        <div class="listling-item-content-input-resource">
                            <div data-content="resourceElem"></div>
                            <div class="micro-overlay micro-panel">
                                <button is="micro-button" type="button" class="action" data-run="attach" data-onclick="onAttachClick">
                                    <i class="fa fa-trash"></i><!-- Remove-->
                                </button>
                            </div>
                        </div>

        .listling-item-content-input-resource {
            position: relative;
        }

        .micro-overlay {
            position: absolute;
            top: var(--micro-size-xs);
            /*right: var(--micro-size-xs);*/
            background: rgba(221, 221, 221, 0.75);
        }

        .listling-item-content-input {
            --micro-link-max-height: calc((70ch - 2 * var(--micro-size-xs)) * 9 / 16);
            --micro-image-max-height: var(--micro-link-max-height);
        }

        .listling-item-content-input-resource {
            padding: var(--micro-size-xs);
        }

        .listling-item-content-input-resource > div:first-child > * {
            display: block;
            width: auto;
        }

            onBlur: () => {
                const pattern = /^https?:\/\/\S+/u;
                const match = this._form.elements.title.value.match(pattern) ||
                    this._form.elements.text.value.match(pattern);
                this._contentInput.resource = match ? match[0] : null;
            },

            attach: () => {
                this._contentInput.resource = result;
                if (!this._form.elements.title.value) {
                    this._form.elements.title.value = "Image"; // result.url;
                }

        this._contentInput = this.querySelector(".micro-input-wrapper");

    edit: () => {
        const resource = this._contentInput.resource && this._contentInput.resource.url;
