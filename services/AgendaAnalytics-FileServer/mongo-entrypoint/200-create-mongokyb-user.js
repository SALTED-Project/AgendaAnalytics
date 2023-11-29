const callWithRetry = async (fn, num_tries = 0) => {
    try {
        return await fn();
    }catch(e) {
        if (num_tries > 5) {
            throw e;
        }
        print('Failed creating user. Retrying soon.')
        await sleep((2 ** num_tries) * 1000);

        return callWithRetry(fn, num_tries + 1);
    }
}

function createUser() {
    db.getSiblingDB("admin").createUser(
        {
            user: "mongouser",
            pwd: "mongopassword",
            roles: [
                {
                    role: "readWriteAnyDatabase",
                    db: "admin"
                },
                {
                    role: "dbAdminAnyDatabase",
                    db: "admin"
                }
            ]
        }
    );
}

callWithRetry(createUser);
