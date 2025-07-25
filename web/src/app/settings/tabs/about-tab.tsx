// SPDX-License-Identifier: MIT

import { BadgeInfo } from "lucide-react";

import { Markdown } from "~/components/agent/markdown";

import about from "./about.md";
import type { Tab } from "./types";

export const AboutTab: Tab = () => {
  return <Markdown>{about}</Markdown>;
};
AboutTab.icon = BadgeInfo;
