const orb = document.getElementById("orb");

const statusText =
    document.getElementById("statusText");

const orbInstruction =
    document.getElementById("orbInstruction");

const resetButton =
    document.getElementById("resetButton");


/* =========================
   STATUS
   ========================= */

function updateStatus(status) {

    orb.classList.remove(
        "listening",
        "thinking",
        "speaking"
    );

    switch (status) {

        case "listening":

            orb.classList.add("listening");

            statusText.textContent =
                "Listening...";

            orbInstruction.textContent =
                "I'm listening";

            break;


        case "thinking":

            orb.classList.add("thinking");

            statusText.textContent =
                "Processing...";

            orbInstruction.textContent =
                "Thinking";

            break;


        case "speaking":

            orb.classList.add("speaking");

            statusText.textContent =
                "E.V. is speaking";

            orbInstruction.textContent =
                "E.V. is responding";

            break;


        default:

            statusText.textContent =
                "E.V. is ready";

            orbInstruction.textContent =
                "Tap the orb to speak";
    }
}


/* =========================
   CHECK PYTHON STATUS
   ========================= */

async function checkStatus() {

    try {

        const response =
            await fetch("/api/status");

        const data =
            await response.json();

        updateStatus(data.status);

    }

    catch (error) {

        statusText.textContent =
            "E.V. offline";
    }
}


setInterval(
    checkStatus,
    500
);


/* =========================
   RESET
   ========================= */

resetButton.addEventListener(
    "click",
    async () => {

        try {

            await fetch(
                "/api/stop",
                {
                    method: "POST"
                }
            );

            updateStatus("idle");

        }

        catch (error) {

            console.error(error);
        }
    }
);


/* =========================
   ORB
   ========================= */

orb.addEventListener(
    "click",
    () => {

        /*
         * The actual microphone is handled
         * by Python/faster-whisper.
         *
         * This button will later be connected
         * to the assistant's listening state.
         */

        orb.classList.add("listening");

        statusText.textContent =
            "Listening...";

        orbInstruction.textContent =
            "I'm listening";
    }
);


checkStatus();