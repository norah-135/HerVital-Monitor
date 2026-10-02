#include <stdint.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* ====================================================================
   1. تعريفات السجلات (STM32L0)
   ==================================================================== */
#define PERIPH_BASE           (0x40000000UL)
#define APB1PERIPH_BASE       (PERIPH_BASE)
#define AHBPERIPH_BASE        (PERIPH_BASE + 0x00020000UL)
#define IOPORT_BASE           (PERIPH_BASE + 0x10000000UL)

/* RCC */
#define RCC_BASE              (AHBPERIPH_BASE + 0x1000UL)
#define RCC_CR                (*(volatile uint32_t *)(RCC_BASE + 0x00))
#define RCC_ICSCR             (*(volatile uint32_t *)(RCC_BASE + 0x04))
#define RCC_CFGR              (*(volatile uint32_t *)(RCC_BASE + 0x0C))
#define RCC_IOPENR            (*(volatile uint32_t *)(RCC_BASE + 0x2C))
#define RCC_APB1ENR           (*(volatile uint32_t *)(RCC_BASE + 0x38))

/* GPIOA */
#define GPIOA_BASE            (IOPORT_BASE + 0x0000UL)
#define GPIOA_MODER           (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_OTYPER          (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_OSPEEDR         (*(volatile uint32_t *)(GPIOA_BASE + 0x08))
#define GPIOA_PUPDR           (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))
#define GPIOA_AFRH            (*(volatile uint32_t *)(GPIOA_BASE + 0x24))

/* I2C1 */
#define I2C1_BASE             (APB1PERIPH_BASE + 0x5400UL)
#define I2C1_CR1              (*(volatile uint32_t *)(I2C1_BASE + 0x00))
#define I2C1_CR2              (*(volatile uint32_t *)(I2C1_BASE + 0x04))
#define I2C1_TIMINGR          (*(volatile uint32_t *)(I2C1_BASE + 0x10))
#define I2C1_ISR              (*(volatile uint32_t *)(I2C1_BASE + 0x18))
#define I2C1_ICR              (*(volatile uint32_t *)(I2C1_BASE + 0x1C))
#define I2C1_TXDR             (*(volatile uint32_t *)(I2C1_BASE + 0x28))

#define ST25DV_ADDR_DATA      0x53

/* ====================================================================
   2. الدوال المساعدة
   ==================================================================== */
static void delay_cycles(volatile uint32_t count)
{
    while (count--) { __asm("nop"); }
}

static void SystemClock_Init(void)
{
    RCC_CR |= (1U << 0);
    while (!(RCC_CR & (1U << 2)));

    RCC_ICSCR &= ~(7U << 13);
    RCC_ICSCR |=  (5U << 13); // 2.097 MHz لاستهلاك طاقة منخفض

    RCC_CFGR &= ~3U;
    while ((RCC_CFGR & (3U << 2)) != 0);
}

static void GPIO_Init(void)
{
    RCC_IOPENR |= (1U << 0);

    // PA9 (SCL) و PA10 (SDA) لوظيفة I2C1 البديلة
    GPIOA_MODER &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_MODER |=  ((2U << (9 * 2)) | (2U << (10 * 2)));

    GPIOA_OTYPER |= (1U << 9) | (1U << 10);
    GPIOA_OSPEEDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));

    GPIOA_PUPDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_PUPDR |=  ((1U << (9 * 2)) | (1U << (10 * 2)));

    GPIOA_AFRH &= ~((0xFU << ((9 - 8) * 4)) | (0xFU << ((10 - 8) * 4)));
    GPIOA_AFRH |=  ((1U << ((9 - 8) * 4)) | (1U << ((10 - 8) * 4)));
}

static void I2C1_Init(void)
{
    RCC_APB1ENR |= (1U << 21);
    I2C1_CR1 &= ~(1U << 0);
    I2C1_TIMINGR = 0x00000509; // 100kHz
    I2C1_CR1 |= (1U << 0);
}

static uint8_t I2C1_WriteData(uint16_t memAddr, const uint8_t *pData, uint16_t size)
{
    uint32_t totalBytes = size + 2;
    uint32_t timeout;
    uint8_t retries = 15;

    while (retries--)
    {
        I2C1_ICR = (1U << 4) | (1U << 5);

        I2C1_CR2 = ((uint32_t)(ST25DV_ADDR_DATA << 1)) | (totalBytes << 16) | (1U << 25);
        I2C1_CR2 |= (1U << 13);

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 1)))
        {
            if (I2C1_ISR & (1U << 4)) goto retry;
            if (--timeout == 0) goto retry;
        }
        I2C1_TXDR = (memAddr >> 8) & 0xFF;

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 1)))
        {
            if (I2C1_ISR & (1U << 4)) goto retry;
            if (--timeout == 0) goto retry;
        }
        I2C1_TXDR = memAddr & 0xFF;

        for (uint16_t i = 0; i < size; i++)
        {
            timeout = 30000;
            while (!(I2C1_ISR & (1U << 1)))
            {
                if (I2C1_ISR & (1U << 4)) goto retry;
                if (--timeout == 0) goto retry;
            }
            I2C1_TXDR = pData[i];
        }

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 5))) { if (--timeout == 0) break; }
        I2C1_ICR = (1U << 5);

        delay_cycles(15000);
        return 0;

    retry:
        I2C1_CR2 |= (1U << 14);
        delay_cycles(4000);
    }
    return 1;
}

static void ST25DV_WriteUriNDEF(float t1, float t2, uint32_t seq)
{
    char urlPayload[80];
    int int1 = (int)t1;
    int frac1 = (int)((t1 - int1) * 10);
    if (frac1 < 0) frac1 = -frac1;

    int int2 = (int)t2;
    int frac2 = (int)((t2 - int2) * 10);
    if (frac2 < 0) frac2 = -frac2;

    snprintf(urlPayload, sizeof(urlPayload),
             "172.20.10.8:5000/update?t1=%d.%d&t2=%d.%d&_=%u",
             int1, frac1, int2, frac2, (unsigned int)seq);

    uint8_t urlLen = (uint8_t)strlen(urlPayload);
    uint8_t payloadLen = 1 + urlLen;
    uint8_t recordLen  = 3 + 1 + payloadLen;

    uint8_t ndefBuffer[110];
    uint8_t idx = 0;

    // 1. CC File (4 Bytes)
    ndefBuffer[idx++] = 0xE1;
    ndefBuffer[idx++] = 0x40;
    ndefBuffer[idx++] = 0x08;
    ndefBuffer[idx++] = 0x01;

    // 2. NDEF Message TLV
    ndefBuffer[idx++] = 0x03;
    ndefBuffer[idx++] = recordLen;

    // 3. Record Header
    ndefBuffer[idx++] = 0xD1;
    ndefBuffer[idx++] = 0x01;
    ndefBuffer[idx++] = payloadLen;
    ndefBuffer[idx++] = 'U';

    // 4. Record Payload
    ndefBuffer[idx++] = 0x03; // "http://"
    memcpy(&ndefBuffer[idx], urlPayload, urlLen);
    idx += urlLen;

    // 5. Terminator TLV
    ndefBuffer[idx++] = 0xFE;

    I2C1_WriteData(0x0000, ndefBuffer, idx);
}

/* ====================================================================
   3. الدالة الرئيسية (تحديث مرحلي أثناء التلامس)
   ==================================================================== */
int main(void)
{
    SystemClock_Init();
    GPIO_Init();
    I2C1_Init();

    // مهلة شحن مكثف الـ VEH واستقرار التغذية من الجوال
    delay_cycles(40000);

    // المرحلة 1: كتابة حرارة الغرفة فور التلامس (24.2C)
    ST25DV_WriteUriNDEF(24.5f, 24.5f, 1);

    // مهلة بقاء الجوال (حوالي 2 إلى 3 ثوانٍ)
    // إذا أبعدتِ الجوال سريعاً سينتهي الأمر هنا ويكون الرابط 24.2
    delay_cycles(250000);

    // المرحلة 2: إذا استمر الجوال ملامساً يتم التحديث لـ 37.1C تلقائياً
    ST25DV_WriteUriNDEF(37.1f, 24.5f, 2);

    delay_cycles(15000);
    I2C1_CR1 &= ~(1U << 0); // إغلاق I2C لتوفير الطاقة وتفريغ الناقل

    while (1)
    {
        __asm("wfi");
    }
}
