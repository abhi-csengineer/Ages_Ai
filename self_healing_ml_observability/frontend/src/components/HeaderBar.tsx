import {
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  IconButton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { MoonIcon, SunIcon } from "@chakra-ui/icons";
import { useEffect, useState } from "react";

interface HeaderBarProps {
  connected: boolean;
  circuitStatus: string;
  tripped: boolean;
  isDarkMode: boolean;
  onToggleTheme: () => void;
}

export function HeaderBar({
  connected,
  circuitStatus,
  tripped,
  isDarkMode,
  onToggleTheme,
}: HeaderBarProps) {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("en-GB"));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const statusLabel = tripped
    ? circuitStatus === "SECURITY_ATTACK"
      ? "Security breach"
      : "Drift alert"
    : "All systems nominal";

  const statusColor = tripped ? "aegis.warning" : "aegis.success";

  return (
    <Box
      as="header"
      bg="aegis.overlay"
      borderBottom="1px solid"
      borderColor="aegis.border"
      backdropFilter="blur(18px)"
      position="sticky"
      top={0}
      zIndex={10}
      transition="background-color 220ms ease, border-color 220ms ease"
    >
      <Flex
        align={{ base: "flex-start", md: "center" }}
        direction={{ base: "column", md: "row" }}
        gap={{ base: 4, md: 6 }}
        justify="space-between"
        maxW="1440px"
        mx="auto"
        px={{ base: 4, md: 6, xl: 8 }}
        py={{ base: 4, md: 3 }}
      >
        <HStack align="center" spacing={3}>
          <Flex
            align="center"
            aria-hidden="true"
            bg="aegis.accentSoft"
            border="1px solid"
            borderColor="aegis.borderStrong"
            borderRadius="xl"
            color="aegis.accent"
            h="42px"
            justify="center"
            shadow="aegis.glow"
            w="42px"
          >
            ⚡
          </Flex>
          <VStack align="flex-start" spacing={0}>
            <Text
              as="h1"
              color="aegis.text"
              fontSize={{ base: "lg", md: "xl" }}
              fontWeight={900}
              letterSpacing="0.08em"
              lineHeight={1.1}
            >
              AEGIS-AI
            </Text>
            <Text
              color="aegis.textMuted"
              fontSize="0.7rem"
              fontWeight={700}
              letterSpacing="0.14em"
              textTransform="uppercase"
            >
              Self-healing ML observability
            </Text>
          </VStack>
        </HStack>

        <Flex
          align={{ base: "stretch", sm: "center" }}
          direction={{ base: "column", sm: "row" }}
          gap={3}
          w={{ base: "100%", md: "auto" }}
        >
          <HStack
            bg="aegis.surface"
            border="1px solid"
            borderColor="aegis.border"
            borderRadius="full"
            px={3}
            py={2}
            spacing={2}
          >
            <Box
              aria-hidden="true"
              bg={statusColor}
              borderRadius="full"
              boxShadow={`0 0 12px ${tripped ? "#FF7A1A" : "#14F195"}`}
              h="8px"
              sx={{ animation: "softPulse 1.8s ease-in-out infinite" }}
              w="8px"
            />
            <Text
              color={statusColor}
              fontSize="0.72rem"
              fontWeight={800}
              letterSpacing="0.08em"
              textTransform="uppercase"
            >
              {statusLabel}
            </Text>
          </HStack>

          <HStack spacing={2}>
            <Badge
              bg={connected ? "aegis.accentSoft" : "aegis.orangeDim"}
              color={connected ? "aegis.success" : "aegis.warning"}
              minW="86px"
              textAlign="center"
            >
              {connected ? "Live" : "Offline"}
            </Badge>
            <Text
              color="aegis.textMuted"
              fontFamily="mono"
              fontSize="0.78rem"
              minW="70px"
              textAlign="center"
            >
              {clock}
            </Text>
            <Button
              display={{ base: "none", sm: "inline-flex" }}
              leftIcon={isDarkMode ? <SunIcon /> : <MoonIcon />}
              onClick={onToggleTheme}
              size="sm"
              variant="outline"
              borderColor="aegis.borderStrong"
              color="aegis.text"
              aria-label={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
            >
              {isDarkMode ? "Light" : "Dark"}
            </Button>
            <IconButton
              aria-label={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
              display={{ base: "inline-flex", sm: "none" }}
              icon={isDarkMode ? <SunIcon /> : <MoonIcon />}
              onClick={onToggleTheme}
              size="sm"
              variant="outline"
              borderColor="aegis.borderStrong"
            />
          </HStack>
        </Flex>
      </Flex>
    </Box>
  );
}
