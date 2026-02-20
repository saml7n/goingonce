import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

const USER_ID_KEY = "goingonce_user_id";
const USER_NAME_KEY = "goingonce_user_name";

export function useIdentity() {
  const [userId] = useState<string>(() => {
    const existing = localStorage.getItem(USER_ID_KEY);
    if (existing) return existing;
    const id = uuidv4();
    localStorage.setItem(USER_ID_KEY, id);
    return id;
  });

  const [userName, setUserNameState] = useState<string>(
    () => localStorage.getItem(USER_NAME_KEY) ?? ""
  );

  const [needsName, setNeedsName] = useState(() => !localStorage.getItem(USER_NAME_KEY));

  const setUserName = useCallback((name: string) => {
    localStorage.setItem(USER_NAME_KEY, name);
    setUserNameState(name);
    setNeedsName(false);
  }, []);

  return { userId, userName, needsName, setUserName };
}
