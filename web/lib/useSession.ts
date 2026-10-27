"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError, HOME_BY_ROLE, Role, User } from "./api";

/** Loads the signed-in user and sends them to the right space for their role. */
export function useSession(expectedRole: Role) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api<User>("/auth/me")
      .then((me) => {
        if (me.role !== expectedRole) router.replace(HOME_BY_ROLE[me.role]);
        else setUser(me);
      })
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) router.replace("/login");
      });
  }, [expectedRole, router]);

  return user;
}
