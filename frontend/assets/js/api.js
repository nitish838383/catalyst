window.SB = {

    apiUrl: () =>
        window.SKILLBRIDGE_CONFIG.API_URL,


    token: () =>
        localStorage.getItem(
            'skillbridge_token'
        ),


    toast(msg) {

        const n =
            document.createElement(
                'div'
            );


        n.className =
            'toast';


        n.textContent =
            msg;


        document.body.appendChild(
            n
        );


        setTimeout(
            () => n.remove(),
            2800
        );

    },


    async request(
        path,
        {
            method = 'GET',
            body,
            headers = {}
        } = {}
    ) {

        const h = {
            'Accept': 'application/json',
            ...headers
        };


        const token =
            this.token();


        if (token) {

            h.Authorization =
                `Bearer ${token}`;

        }


        let payload =
            body;


        if (
            body &&
            !(body instanceof FormData) &&
            typeof body !== 'string'
        ) {

            h['Content-Type'] =
                'application/json';


            payload =
                JSON.stringify(
                    body
                );

        }


        const res =
            await fetch(
                `${this.apiUrl()}${path}`,
                {
                    method,
                    headers: h,
                    body: payload
                }
            );


        let data = {};


        try {

            data =
                await res.json();

        }

        catch {

        }


        if (!res.ok) {

            const detail =
                data.detail ||
                data.message ||
                `Request failed (${res.status})`;


            throw new Error(
                typeof detail === 'string'
                    ? detail
                    : JSON.stringify(detail)
            );

        }


        return data;

    },


    get(path) {

        return this.request(
            path
        );

    },


    post(path, body) {

        return this.request(
            path,
            {
                method: 'POST',
                body
            }
        );

    },


    patch(path, body) {

        return this.request(
            path,
            {
                method: 'PATCH',
                body
            }
        );

    },


    del(path) {

        return this.request(
            path,
            {
                method: 'DELETE'
            }
        );

    },


    esc(v) {

        return String(v ?? '')
            .replace(
                /[&<>'"]/g,
                c => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    "'": '&#39;',
                    '"': '&quot;'
                }[c])
            );

    },


    qs(k) {

        return new URLSearchParams(
            location.search
        ).get(k);

    },


    fmtDate(v) {

        if (!v) {
            return '—';
        }


        try {

            return new Date(v)
                .toLocaleDateString();

        }

        catch {

            return v;

        }

    },

};