const API_URL = 'http://localhost:8000/data';

export function fetch_data(): Promise<any> {
    return window
        .fetch(API_URL)
        .then((response) => {
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                // throw new Error(`HTTP error! status: ${response.status}`);
            }
            let x = response.json();
            console.log(x);
            return x;
        })
        .catch((err) => {
            console.log(err);
        });
}
