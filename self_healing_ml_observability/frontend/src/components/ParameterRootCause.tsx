import {
  Box, Flex, VStack, HStack, Text, Progress, Badge,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { ParameterDrift } from "../types/contracts";
import { useMemo } from "react";

interface ParameterRootCauseProps {
  parameters: ParameterDrift[];
}

const MotionBadge = motion(Badge);

export function ParameterRootCause({ parameters }: ParameterRootCauseProps) {
  /* Find the parameter with the highest drift */
  const criticalIdx = useMemo(() => {
    let maxIdx = 0;
    let maxVal = -1;
    parameters.forEach((p, i) => {
      if (p.drift > maxVal) {
        maxVal = p.drift;
        maxIdx = i;
      }
    });
    return maxVal > 0.15 ? maxIdx : -1;
  }, [parameters]);

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
          TILE-E // PARAMETER ROOT-CAUSE HUB
        </Text>
        <Badge bg="aegis.limeDim" color="aegis.lime" fontSize="0.45rem" px={2}>
          JUDGE REQ C
        </Badge>
      </Flex>

      {/* Progress bars */}
      <VStack flex={1} spacing={0} align="stretch" overflow="auto" p={3} minH={0}>
        {parameters.map((param, idx) => {
          const isCritical = idx === criticalIdx;
          const pctValue = Math.min(100, param.drift * 100);
          const barColor = isCritical ? "orange" : "green";
          const textColor = isCritical ? "aegis.orange" : "aegis.lime";

          return (
            <Box
              key={param.name}
              py={2.5}
              px={2}
              borderBottom="1px solid"
              borderColor="rgba(45,55,72,0.4)"
              bg={isCritical ? "rgba(255,77,0,0.05)" : "transparent"}
              borderLeft={isCritical ? "3px solid" : "1px solid"}
              borderLeftColor={isCritical ? "aegis.orange" : "transparent"}
            >
              <Flex justify="space-between" align="center" mb={1.5}>
                <HStack spacing={2}>
                  <Text
                    fontSize="0.65rem"
                    color={textColor}
                    fontWeight={isCritical ? 800 : 500}
                    letterSpacing="0.1em"
                  >
                    {param.label}
                  </Text>
                  {isCritical && (
                    <MotionBadge
                      bg="rgba(255,77,0,0.2)"
                      color="aegis.orange"
                      fontSize="0.45rem"
                      px={2}
                      py={0.5}
                      animate={{ opacity: [1, 0.4, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                    >
                      ⚠ CRITICAL PARAMETER
                    </MotionBadge>
                  )}
                </HStack>
                <Text
                  fontSize="0.65rem"
                  color={textColor}
                  fontWeight={700}
                >
                  {(param.drift * 100).toFixed(1)}%
                </Text>
              </Flex>

              <Progress
                value={pctValue}
                size="sm"
                colorScheme={barColor}
                bg="rgba(204,255,0,0.06)"
                h="8px"
                borderRadius="0 !important"
                sx={{
                  "& > div": {
                    borderRadius: "0 !important",
                    transition: "width 0.6s ease-out",
                  },
                }}
              />
            </Box>
          );
        })}
      </VStack>
    </Box>
  );
}
