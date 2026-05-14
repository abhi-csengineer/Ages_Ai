import { Box, Flex, Text, type BoxProps } from "@chakra-ui/react";
import type { ReactNode } from "react";

interface DashboardCardProps extends BoxProps {
  eyebrow: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
  isAlert?: boolean;
}

export function DashboardCard({
  eyebrow,
  title,
  action,
  children,
  isAlert = false,
  ...boxProps
}: DashboardCardProps) {
  return (
    <Box
      as="section"
      h="100%"
      bg="aegis.surface"
      border="1px solid"
      borderColor={isAlert ? "aegis.danger" : "aegis.border"}
      borderRadius="2xl"
      boxShadow="aegis.card"
      display="flex"
      flexDir="column"
      overflow="hidden"
      transition="background-color 220ms ease, border-color 220ms ease, box-shadow 220ms ease, transform 180ms ease"
      _hover={{ transform: "translateY(-2px)", boxShadow: "aegis.glow" }}
      {...boxProps}
    >
      <Flex
        align={{ base: "flex-start", sm: "center" }}
        borderBottom="1px solid"
        borderColor="aegis.border"
        direction={{ base: "column", sm: "row" }}
        gap={2}
        justify="space-between"
        px={{ base: 4, md: 5 }}
        py={3}
      >
        <Box>
          <Text
            color="aegis.textFaint"
            fontSize="0.68rem"
            fontWeight={800}
            letterSpacing="0.14em"
            textTransform="uppercase"
          >
            {eyebrow}
          </Text>
          <Text color="aegis.text" fontSize="sm" fontWeight={800} mt={0.5}>
            {title}
          </Text>
        </Box>
        {action}
      </Flex>

      <Box flex={1} minH={0} overflow="hidden">
        {children}
      </Box>
    </Box>
  );
}
