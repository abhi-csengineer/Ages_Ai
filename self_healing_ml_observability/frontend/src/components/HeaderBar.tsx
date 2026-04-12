import { Box, Flex, HStack, Text, Badge } from "@chakra-ui/react";
import { useEffect, useState } from "react";

interface HeaderBarProps {
  connected: boolean;
  circuitStatus: string;
  tripped: boolean;
}

export function HeaderBar({ connected, circuitStatus, tripped }: HeaderBarProps) {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("en-GB"));
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, []);

  const statusLabel = tripped
    ? circuitStatus === "SECURITY_ATTACK"
      ? "SECURITY BREACH"
      : "DRIFT ALERT"
    : "ALL SYSTEMS NOMINAL";

  const statusColor = tripped ? "aegis.orange" : "aegis.lime";

  return (
    <Flex
      h="36px"
      bg="aegis.black"
      borderBottom="1px solid"
      borderColor="aegis.border"
      align="center"
      px={4}
      justify="space-between"
      flexShrink={0}
    >
      {/* Left: Brand */}
      <HStack spacing={3}>
        <Text fontSize="0.75rem" fontWeight={800} color="aegis.lime" letterSpacing="0.15em">
          ⚡ AEGIS-AI
        </Text>
        <Text fontSize="0.55rem" color="aegis.textDim" letterSpacing="0.15em">
          // TACTICAL COMMAND
        </Text>
      </HStack>

      {/* Center: Status */}
      <HStack spacing={2}>
        <Box
          w="6px"
          h="6px"
          bg={statusColor}
          boxShadow={`0 0 6px ${tripped ? "#FF4D00" : "#CCFF00"}`}
        />
        <Text fontSize="0.6rem" color={statusColor} letterSpacing="0.1em" fontWeight={600}>
          {statusLabel}
        </Text>
      </HStack>

      {/* Right: Connection + Clock */}
      <HStack spacing={3}>
        <Badge
          bg={connected ? "aegis.limeDim" : "aegis.orangeDim"}
          color={connected ? "aegis.lime" : "aegis.orange"}
          fontSize="0.5rem"
          px={2}
          py={0.5}
        >
          {connected ? "⚡ LIVE" : "◌ OFFLINE"}
        </Badge>
        <Text fontSize="0.6rem" color="aegis.textDim" letterSpacing="0.08em">
          {clock}
        </Text>
      </HStack>
    </Flex>
  );
}
