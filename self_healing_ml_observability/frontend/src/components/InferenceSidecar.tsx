import {
  Box,
  Flex,
  HStack,
  VStack,
  Text,
  Input,
  IconButton,
  Button,
} from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useEffect, useRef, useState } from "react";
import { inferSidecar } from "../hooks/useApi";
import { SecurityLogEntry } from "../types/contracts";

interface InferenceSidecarProps {
  securityLog: SecurityLogEntry[];
}

const TAG_COLORS: Record<SecurityLogEntry["type"], { bg: string; color: string; tag: string }> = {
  BLOCKED: { bg: "rgba(255,0,51,0.15)", color: "#FF0033", tag: "[BLKD]" },
  REDACTED: { bg: "rgba(255,77,0,0.15)", color: "#FF4D00", tag: "[RDCT]" },
  PASSED: { bg: "rgba(204,255,0,0.08)", color: "#CCFF00", tag: "[PASS]" },
  ANOMALY: { bg: "rgba(255,214,0,0.12)", color: "#FFD600", tag: "[ANOM]" },
};

export function InferenceSidecar({ securityLog }: InferenceSidecarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const sendingRef = useRef(false);
  const [prompt, setPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [liveMode, setLiveMode] = useState(true);
  const [lastDrift, setLastDrift] = useState<number | null>(null);
  const [lastVigor, setLastVigor] = useState<number | null>(null);
  const [lastModel, setLastModel] = useState<string>("-");

  const LIVE_PROMPTS = [
    "Summarize safe deployment controls in one sentence.",
    "List one model risk and one mitigation in a short line.",
    "Respond with one compliance-focused monitoring insight.",
    "Provide one operational drift warning signal.",
  ];

  const runInference = async (inputPrompt: string) => {
    const text = inputPrompt.trim();
    if (!text || sendingRef.current) {
      return;
    }
    sendingRef.current = true;
    setIsSending(true);
    setErrorText(null);
    try {
      const resp = await inferSidecar({
        request_id: typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}`,
        prompt: text,
        population_id: 0,
        demographic_group: "general",
      });
      setLastDrift(resp.drift);
      setLastVigor(resp.vigor);
      setLastModel(resp.provider_model);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "inference_failed");
    } finally {
      sendingRef.current = false;
      setIsSending(false);
    }
  };

  const handleSend = async () => {
    await runInference(prompt);
    setPrompt("");
  };

  useEffect(() => {
    if (!liveMode) {
      return;
    }
    let cursor = 0;

    const tick = async () => {
      const fallbackPrompt = LIVE_PROMPTS[cursor % LIVE_PROMPTS.length];
      cursor += 1;
      const activePrompt = prompt.trim() || fallbackPrompt;
      await runInference(activePrompt);
    };

    tick();
    const timer = window.setInterval(tick, 4000);
    return () => window.clearInterval(timer);
  }, [liveMode, prompt]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [securityLog]);

  return (
    <Box
      h="100%"
      bg="aegis.black"
      border="1px solid"
      borderColor="aegis.border"
      display="flex"
      flexDir="column"
      overflow="hidden"
    >
      {/* Header */}
      <Flex
        px={3}
        py={1.5}
        borderBottom="1px solid"
        borderColor="aegis.border"
        justify="space-between"
        align="center"
        flexShrink={0}
      >
        <Text fontSize="0.55rem" color="aegis.textDim" letterSpacing="0.15em">
          TILE-C // INFERENCE SIDECAR
        </Text>
        <Text fontSize="0.5rem" color="aegis.lime" opacity={0.4}>
          ▸
        </Text>
      </Flex>

      {/* Scrolling log */}
      <VStack
        ref={scrollRef}
        flex={1}
        spacing={0}
        align="stretch"
        overflow="auto"
        p={0}
        minH={0}
      >
        {securityLog.map((entry, i) => {
          const cfg = TAG_COLORS[entry.type];
          const ts = new Date(entry.timestamp).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
          return (
            <Box key={`${entry.timestamp}-${i}`} px={2} py={1} bg={cfg.bg} borderBottom="1px solid" borderColor="rgba(45,55,72,0.3)">
              <Text fontSize="0.55rem" lineHeight="1.4" wordBreak="break-word">
                <Text as="span" color="aegis.textDim" mr={1}>{ts}</Text>
                <Text as="span" color={cfg.color} fontWeight={700} mr={1}>{cfg.tag}</Text>
                <Text as="span" color="aegis.text">{entry.message}</Text>
              </Text>
            </Box>
          );
        })}
      </VStack>

      {/* Prompt input */}
      <HStack
        px={2}
        py={1}
        borderTop="1px solid"
        borderColor="aegis.border"
        justify="space-between"
      >
        <HStack spacing={3}>
          <Text fontSize="0.55rem" color={liveMode ? "aegis.lime" : "aegis.textDim"}>
            MODE: {liveMode ? "LIVE" : "MANUAL"}
          </Text>
          <Text fontSize="0.55rem" color="aegis.textDim">
            DRIFT: {lastDrift === null ? "--" : `${lastDrift.toFixed(2)}%`}
          </Text>
          <Text fontSize="0.55rem" color="aegis.textDim">
            VIGOR: {lastVigor === null ? "--" : lastVigor.toFixed(3)}
          </Text>
        </HStack>
        <Button
          size="xs"
          variant="outline"
          borderColor={liveMode ? "aegis.lime" : "aegis.border"}
          color={liveMode ? "aegis.lime" : "aegis.textDim"}
          onClick={() => setLiveMode((v) => !v)}
        >
          {liveMode ? "Stop Live" : "Start Live"}
        </Button>
      </HStack>

      <HStack
        px={2}
        py={1.5}
        borderTop="1px solid"
        borderColor="aegis.border"
        spacing={1}
        flexShrink={0}
      >
        <Text fontSize="0.55rem" color="aegis.lime" flexShrink={0}>▸_</Text>
        <Input
          size="xs"
          variant="unstyled"
          placeholder="gemini sidecar prompt (used by live mode too)..."
          color="aegis.text"
          fontSize="0.6rem"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          _placeholder={{ color: "aegis.textDim" }}
        />
        <IconButton
          aria-label="send"
          icon={<ArrowForwardIcon />}
          size="xs"
          variant="ghost"
          color="aegis.lime"
          _hover={{ bg: "aegis.limeDim" }}
          isDisabled={!prompt.trim() || isSending}
          isLoading={isSending}
          onClick={handleSend}
        />
      </HStack>
      {errorText ? (
        <Box px={2} py={1} borderTop="1px solid" borderColor="aegis.border">
          <Text fontSize="0.55rem" color="aegis.red">{errorText}</Text>
        </Box>
      ) : null}
      <Box px={2} py={1} borderTop="1px solid" borderColor="aegis.border">
        <Text fontSize="0.55rem" color="aegis.textDim" noOfLines={1}>
          MODEL: {lastModel}
        </Text>
      </Box>
    </Box>
  );
}
