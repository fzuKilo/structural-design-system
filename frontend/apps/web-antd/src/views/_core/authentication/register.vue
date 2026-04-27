<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, h, ref } from 'vue';

import { AuthenticationRegister, z } from '@vben/common-ui';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';

import { $t } from '@vben/locales';

import { registerApi } from '#/api/core/auth';

defineOptions({ name: 'Register' });

const loading = ref(false);
const router = useRouter();

const formSchema = computed((): VbenFormSchema[] => {
  return [
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: $t('authentication.usernameTip'),
      },
      fieldName: 'username',
      label: $t('authentication.username'),
      rules: z.string().min(3, { message: '用户名至少3个字符' }),
    },
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: $t('authentication.emailTip'),
        type: 'email',
      },
      fieldName: 'email',
      label: $t('authentication.email'),
      rules: z.string().email({ message: $t('authentication.emailValidErrorTip') }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        passwordStrength: true,
        placeholder: $t('authentication.password'),
      },
      fieldName: 'password',
      label: $t('authentication.password'),
      renderComponentContent() {
        return {
          strengthText: () => $t('authentication.passwordStrength'),
        };
      },
      rules: z.string().min(6, { message: '密码至少6个字符' }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: $t('authentication.confirmPassword'),
      },
      dependencies: {
        rules(values) {
          const { password } = values;
          return z
            .string({ required_error: $t('authentication.passwordTip') })
            .min(1, { message: $t('authentication.passwordTip') })
            .refine((value) => value === password, {
              message: $t('authentication.confirmPasswordTip'),
            });
        },
        triggerFields: ['password'],
      },
      fieldName: 'confirmPassword',
      label: $t('authentication.confirmPassword'),
    },
    {
      component: 'VbenCheckbox',
      fieldName: 'agreePolicy',
      renderComponentContent: () => ({
        default: () =>
          h('span', [
            $t('authentication.agree'),
            h(
              'a',
              { class: 'vben-link ml-1', href: '' },
              `${$t('authentication.privacyPolicy')} & ${$t('authentication.terms')}`,
            ),
          ]),
      }),
      rules: z.boolean().refine((value) => !!value, {
        message: $t('authentication.agreeTip'),
      }),
    },
  ];
});

async function handleSubmit(value: Recordable<any>) {
  loading.value = true;
  try {
    await registerApi({ username: value.username, email: value.email, password: value.password });
    message.success('注册成功，请登录');
    router.push('/auth/login');
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '注册失败，请重试';
    message.error(detail);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AuthenticationRegister
    :form-schema="formSchema"
    :loading="loading"
    @submit="handleSubmit"
  />
</template>
